"""Wire the codeowner tasks feature into SGTM's pull request sync.

`sync` runs on every full pull request sync and on every review event, once
the PR's Asana task exists. It

* reads CODEOWNERS from the branch GitHub evaluates the PR against (the stack
  base for a GitHub-native stack, otherwise the PR's base branch),
* groups the changed files into owner sets and evaluates each one against the
  PR's reviews,
* posts SGTM's GitHub comments: the heads-up for opted-in authors, and the
  confirmation once the label is added,
* creates and maintains the Asana subtasks once the author adds the label,
  requesting reviews on GitHub from newly assigned codeowners,
* moves the PR's GitHub assignee following the codeowner rules, and
* persists everything in the per-PR `CodeownerState`.

It returns the `CodeownerTaskContext` the Asana side needs, or None when the
feature is off or the sync failed. In that case the PR task is updated exactly
as it was before this feature existed, so a GitHub permission problem or an
outage in one of the lookups degrades to today's behaviour.
"""
import hashlib
import time
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

import src.asana.client as asana_client
import src.aws.s3_client as s3_client
import src.config as config
import src.github.client as github_client
import src.github.graphql.client as github_graphql_client
from src.asana.mentions import task_url_from_task_id
from src.github.helpers import pull_request_has_label
from src.github.models import PullRequest, Review
from src.logger import logger

from . import texts
from .codeowners_file import CODEOWNERS_PATHS, CodeownersRule, parse_codeowners
from .context import CodeownerTaskContext
from .pr_assignment import (
    TRIGGER_REVIEW,
    TRIGGER_SYNC,
    TRIGGER_TASKS_CREATED,
    decide_pull_request_assignee,
)
from .requirements import OwnerSet, codeowned_files, requirements_for_files
from .state import CodeownerState, now_iso
from .status import (
    CodeownerSummary,
    RequirementStatus,
    evaluate_requirement,
)
from .tasks import SubtaskSyncInputs, sync_subtasks

_CACHE_TTL_SECONDS = 300

# org/slug -> (fetched at, member logins)
_team_members_cache: Dict[str, Tuple[float, Set[str]]] = {}
# owner/repo@ref -> (fetched at, rules)
_codeowners_cache: Dict[str, Tuple[float, List[CodeownersRule]]] = {}
# owner/repo values whose label was confirmed to exist in this process.
_labels_ensured: Set[str] = set()


def reset_caches() -> None:
    """For tests."""
    _team_members_cache.clear()
    _codeowners_cache.clear()
    _labels_ensured.clear()


# --------------------------------------------------------------------------
# Lookups
# --------------------------------------------------------------------------


def team_members(org: str, team_slug: str) -> Set[str]:
    key = f"{org}/{team_slug}"
    now = time.monotonic()
    cached = _team_members_cache.get(key)
    if cached is not None and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]
    members = set(github_graphql_client.get_team_members(org, team_slug))
    _team_members_cache[key] = (now, members)
    return members


def resolve_pool(owner_set: OwnerSet) -> Set[str]:
    """Every GitHub login that may approve for `owner_set`."""
    logins: Set[str] = set(owner_set.individual_logins())
    for slug in owner_set.team_slugs():
        org, team = slug.split("/", 1)
        logins |= team_members(org, team)
    return logins


def codeowners_rules(
    org_name: str, owner: str, repository: str, ref: str
) -> List[CodeownersRule]:
    """Parsed CODEOWNERS at `ref`, looked up where GitHub looks. Empty when
    the repository has no CODEOWNERS file."""
    key = f"{owner}/{repository}@{ref}"
    now = time.monotonic()
    cached = _codeowners_cache.get(key)
    if cached is not None and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]
    rules: List[CodeownersRule] = []
    for path in CODEOWNERS_PATHS:
        text = github_graphql_client.get_repository_file_content(
            org_name, owner, repository, ref, path
        )
        if text is not None:
            rules = parse_codeowners(text)
            break
    _codeowners_cache[key] = (now, rules)
    return rules


class OutOfOfficeLookup(object):
    """Out-of-office end date per GitHub login, from Asana, memoised per sync.

    Without a configured workspace nobody is treated as out of office.
    """

    def __init__(self, today: Optional[date] = None):
        self.today = today or datetime.now(timezone.utc).date()
        self._cache: Dict[str, Optional[date]] = {}

    def __call__(self, login: str) -> Optional[date]:
        workspace_id = config.SGTM_FEATURE__CODEOWNER_TASKS_ASANA_WORKSPACE_ID
        if not workspace_id:
            return None
        if login not in self._cache:
            user_id = s3_client.get_asana_domain_user_id_from_github_handle(login)
            self._cache[login] = (
                asana_client.out_of_office_until(user_id, workspace_id, self.today)
                if user_id
                else None
            )
        return self._cache[login]


# --------------------------------------------------------------------------
# GitHub side effects
# --------------------------------------------------------------------------


def _is_open(pull_request: PullRequest) -> bool:
    return not pull_request.closed()


def _ensure_label(pull_request: PullRequest, label: str) -> None:
    key = pull_request.repository_full_name()
    if key in _labels_ensured:
        return
    try:
        github_client.ensure_label(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            label,
            texts.LABEL_COLOR,
            texts.label_description(),
        )
        _labels_ensured.add(key)
    except Exception as e:
        logger.warning(f"Could not ensure label '{label}' exists in {key}: {e}")


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


# Stored when a comment was posted but GitHub returned no id: SGTM then knows
# not to post again, and knows it cannot edit that comment either.
UNKNOWN_COMMENT_ID = -1


def _is_known(comment_id: Optional[int]) -> bool:
    return comment_id is not None and comment_id >= 0


def _heads_up_body(pull_request: PullRequest, summary: CodeownerSummary, label: str):
    return texts.heads_up_comment(
        summary.codeowned_files,
        len(summary.evaluations),
        label,
        pull_request.base_ref_name(),
        pull_request.default_branch_name(),
        pull_request.is_in_native_stack(),
    )


def _post_or_edit_heads_up(
    pull_request: PullRequest, summary: CodeownerSummary, state: CodeownerState, label
) -> None:
    """Opted-in authors get a heads-up as soon as the PR touches codeowned
    files, kept current until the label is added."""
    if not s3_client.is_opted_in_to_codeowner_tasks(pull_request.author_handle()):
        return
    body = _heads_up_body(pull_request, summary, label)
    body_hash = _hash(body)
    if state.heads_up_comment_id is None:
        comment_id = github_client.add_pr_comment(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            pull_request.number(),
            body,
        )
        # UNKNOWN_COMMENT_ID keeps SGTM from posting again when GitHub gave no id.
        state.heads_up_comment_id = (
            comment_id if comment_id is not None else UNKNOWN_COMMENT_ID
        )
        state.heads_up_body_hash = body_hash
        logger.info(f"Posted codeowner heads-up comment {comment_id}")
    elif _is_known(state.heads_up_comment_id) and body_hash != state.heads_up_body_hash:
        github_client.edit_comment(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            pull_request.number(),
            state.heads_up_comment_id,
            body,
        )
        state.heads_up_body_hash = body_hash


def _announce_created(
    pull_request: PullRequest, summary: CodeownerSummary, state: CodeownerState, label
) -> None:
    """Tell the author on GitHub which subtasks exist and who holds them: by
    editing the heads-up comment when there is one, otherwise in a new
    comment that also introduces the feature."""
    owner_sets = {
        e.owner_set.key(): e.owner_set
        for e in summary.evaluations
        if e.owner_set.key() in state.subtasks
    }
    assignees = {key: state.subtasks[key].assignee for key in owner_sets}
    subtask_urls = {
        key: task_url_from_task_id(state.subtasks[key].task_id) for key in owner_sets
    }
    reasons = {key: state.subtasks[key].assignment_reason for key in owner_sets}
    owner = pull_request.repository_owner_handle()
    repository = pull_request.repository_name()
    number = pull_request.number()

    if _is_known(state.heads_up_comment_id):
        body = (
            _heads_up_body(pull_request, summary, label)
            + "\n"
            + texts.created_block_markdown(assignees, subtask_urls, owner_sets, reasons)
        )
        github_client.edit_comment(
            owner, repository, number, state.heads_up_comment_id, body
        )
        state.heads_up_body_hash = _hash(body)
        state.created_comment_id = state.heads_up_comment_id
        return

    body = texts.label_added_comment(
        label, summary.codeowned_files, assignees, subtask_urls, owner_sets, reasons
    )
    comment_id = github_client.add_pr_comment(owner, repository, number, body)
    state.created_comment_id = (
        comment_id if comment_id is not None else UNKNOWN_COMMENT_ID
    )


def _request_reviews(pull_request: PullRequest, logins: List[str]) -> None:
    reviewers = sorted(
        {login for login in logins if login != pull_request.author_handle()}
    )
    if not reviewers or not _is_open(pull_request):
        return
    try:
        github_client.request_reviewers(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            pull_request.number(),
            reviewers,
        )
    except Exception as e:
        logger.warning(f"Could not request reviews from {reviewers}: {e}")


def _assign_pull_request(
    pull_request: PullRequest, state: CodeownerState, login: str
) -> None:
    github_client.set_pull_request_assignee(
        pull_request.repository_owner_handle(),
        pull_request.repository_name(),
        pull_request.number(),
        login,
    )
    # so the Asana task mirrors the new assignee without another query
    pull_request.set_assignees([login])
    if login != pull_request.author_handle():
        state.remember_sgtm_assigned(login)
    logger.info(f"Assigned pull request {pull_request.id()} to {login}")


# --------------------------------------------------------------------------
# State bookkeeping
# --------------------------------------------------------------------------


def _remember_human_choices(pull_request: PullRequest, state: CodeownerState) -> None:
    """Reviewers a person asked for, and assignees a person set, minus the ones
    SGTM itself requested or assigned. GitHub forgets a review request once
    the person reviews, so these accumulate in state."""
    author = pull_request.author_handle()
    chosen = [
        login
        for login in pull_request.human_requested_reviewer_logins()
        if login != author and login not in state.sgtm_requested_logins
    ]
    chosen += [
        login
        for login in pull_request.assignees()
        if login != author and login not in state.sgtm_assigned_logins
    ]
    state.remember_human_chosen(chosen)


def _maybe_comment_all_approved(
    task_id: str, summary: CodeownerSummary, state: CodeownerState
) -> None:
    if state.all_approved_commented or not summary.evaluations:
        return
    approved = [
        e for e in summary.evaluations if e.status is RequirementStatus.APPROVED
    ]
    if not approved or not summary.all_requirements_satisfied():
        return
    asana_client.add_comment(task_id, texts.parent_all_approved_comment(summary))
    state.all_approved_commented = True


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def sync(
    pull_request: PullRequest,
    task_id: str,
    review: Optional[Review] = None,
    now: Optional[datetime] = None,
) -> Optional[CodeownerTaskContext]:
    """Bring the PR's codeowner comments, subtasks and assignee up to date.

    `review` is the review that triggered this sync, when there is one; it
    drives the PR assignment rules. Returns None when the feature is disabled
    or the sync failed, so callers fall back to SGTM's plain behaviour.
    """
    if not config.SGTM_FEATURE__CODEOWNER_TASKS_ENABLED:
        return None
    pull_request_id = pull_request.id()
    state = CodeownerState.load(pull_request_id)
    before = state.to_document()
    try:
        return _sync(pull_request, task_id, state, review, now)
    except Exception as e:
        logger.error(
            f"Codeowner tasks sync failed for pull request {pull_request_id}: {e}",
            exc_info=True,
        )
        return None
    finally:
        if state.to_document() != before:
            state.save(pull_request_id)


def _sync(
    pull_request: PullRequest,
    task_id: str,
    state: CodeownerState,
    review: Optional[Review],
    now: Optional[datetime],
) -> CodeownerTaskContext:
    now = now or datetime.now(timezone.utc)
    org_name = pull_request.repository_owner_handle()
    label = config.SGTM_FEATURE__CODEOWNER_TASKS_LABEL
    author = pull_request.author_handle()

    # -- what GitHub requires ------------------------------------------------
    github_graphql_client.load_all_changed_files(org_name, pull_request)
    ref = pull_request.stack_base_ref_name() or pull_request.base_ref_name()
    rules = codeowners_rules(org_name, org_name, pull_request.repository_name(), ref)
    files = pull_request.changed_files()
    owned = codeowned_files(rules, files)
    requirements = requirements_for_files(rules, files)

    # Resolve every pool before any side effect so that a GitHub failure
    # aborts the sync cleanly instead of half-applying it.
    codeowner_logins: Set[str] = set()
    for owner_set in set(owned.values()):
        codeowner_logins |= resolve_pool(owner_set)

    _remember_human_choices(pull_request, state)

    if (
        not state.tasks_requested
        and _is_open(pull_request)
        and not pull_request.is_draft()
        and pull_request_has_label(pull_request, label)
    ):
        state.tasks_requested_at = now_iso()
        logger.info(f"Codeowner tasks requested for pull request {pull_request.id()}")

    evaluations = [
        evaluate_requirement(
            requirement,
            resolve_pool,
            pull_request.reviews(),
            author,
            merged=pull_request.merged(),
        )
        for requirement in requirements
    ]
    summary = CodeownerSummary(
        evaluations=evaluations,
        codeowned_files=owned,
        tasks_requested=state.tasks_requested,
        codeowner_logins=codeowner_logins,
        human_chosen_logins=set(state.human_chosen_logins),
    )

    # -- GitHub comments and label -------------------------------------------
    if owned and _is_open(pull_request):
        _ensure_label(pull_request, label)
        if not state.tasks_requested:
            _post_or_edit_heads_up(pull_request, summary, state, label)

    # -- Asana subtasks ---------------------------------------------------------
    trigger = TRIGGER_SYNC
    if state.tasks_requested and not pull_request.is_draft():
        result = sync_subtasks(
            SubtaskSyncInputs(
                pull_request=pull_request,
                parent_task_id=task_id,
                summary=summary,
                state=state,
                resolve_pool=resolve_pool,
                out_of_office_until=OutOfOfficeLookup(now.date()),
                now=now,
            )
        )
        _request_reviews(pull_request, result.newly_assigned_logins)
        if result.created_owner_keys:
            trigger = TRIGGER_TASKS_CREATED
            if state.created_comment_id is None and _is_open(pull_request):
                _announce_created(pull_request, summary, state, label)
        _maybe_comment_all_approved(task_id, summary, state)

    # -- who holds the PR ---------------------------------------------------------
    if review is not None:
        if review.author_handle() in config.SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS:
            review = None
        else:
            trigger = TRIGGER_REVIEW
    context = CodeownerTaskContext(summary, state, label)
    if context.manages_pull_request_assignee():
        target = decide_pull_request_assignee(
            pull_request, summary, state, trigger, review
        )
        if target is not None:
            _assign_pull_request(pull_request, state, target)
    return context
