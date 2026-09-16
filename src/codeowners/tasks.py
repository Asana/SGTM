"""Create, assign, update, complete and reopen codeowner subtasks in Asana.

`sync_subtasks` is idempotent: it compares the PR's current codeowner
evaluation with the persisted `CodeownerState` and applies only the
differences, posting a comment for every transition a person would want to
hear about. The controller (GitHub side) decides *when* to call it and acts on
its result (for example requesting reviews on GitHub from new assignees).
"""
import hashlib
import random
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Callable, Dict, List, Optional, Set

import src.asana.client as asana_client
import src.asana.helpers as asana_helpers
import src.aws.s3_client as s3_client
import src.config as config
from src.github.models import PullRequest
from src.logger import logger

from . import texts
from .assignment import (
    REASON_ENGAGED,
    REASON_HUMAN_REQUESTED,
    REASON_NOBODY_AVAILABLE,
    AssigneeChoice,
    business_days_between,
    choose_assignee,
    is_idle,
)
from .state import CodeownerState, SubtaskState, parse_iso
from .status import (
    CodeownerSummary,
    PoolResolver,
    RequirementEvaluation,
    RequirementStatus,
)

# Returns the last day of the person's current out-of-office entry (date.max
# when open-ended), or None when they are available.
OutOfOfficeLookup = Callable[[str], Optional[date]]

FIELD_APPROVAL = "Codeowner Approval (SGTM)"
FIELD_CODEOWNERS = "Codeowners (SGTM)"
FIELD_PR_STATUS = "PR Status"
FIELD_AUTHOR = "Author (SGTM)"
FIELD_BRANCH_NAME = "Branch Name (SGTM)"


@dataclass
class SubtaskSyncInputs:
    pull_request: PullRequest
    parent_task_id: str
    summary: CodeownerSummary
    state: CodeownerState
    resolve_pool: PoolResolver
    out_of_office_until: OutOfOfficeLookup
    now: datetime
    rng: Optional[random.Random] = None


@dataclass
class SubtaskSyncResult:
    # Logins SGTM assigned during this sync; the controller requests their
    # review on GitHub.
    newly_assigned_logins: List[str] = field(default_factory=list)
    created_owner_keys: List[str] = field(default_factory=list)


class _Sync:
    def __init__(self, inputs: SubtaskSyncInputs):
        self.inputs = inputs
        self.pull_request = inputs.pull_request
        self.state = inputs.state
        self.summary = inputs.summary
        self.result = SubtaskSyncResult()
        self._project_fields: Optional[Dict[str, dict]] = None
        self.author = self.pull_request.author_handle()
        self.several_sets = len(self.summary.evaluations) > 1

    # -- lookups ----------------------------------------------------------

    def _now_iso(self) -> str:
        """Timestamps come from the sync's clock so idleness is measured against
        the same instant they were written with."""
        return self.inputs.now.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _gid(self, login: Optional[str]) -> Optional[str]:
        if login is None:
            return None
        return s3_client.get_asana_domain_user_id_from_github_handle(login)

    def _has_mapping(self, login: str) -> bool:
        return self._gid(login) is not None

    def _is_out_of_office(self, login: str) -> bool:
        try:
            return self.inputs.out_of_office_until(login) is not None
        except Exception as e:
            logger.warning(f"Out-of-office lookup failed for {login}: {e}")
            return False

    def _engaged_logins(self) -> Set[str]:
        logins = {review.author_handle() for review in self.pull_request.reviews()}
        logins |= {comment.author_handle() for comment in self.pull_request.comments()}
        return logins - {self.author}

    def _engaged_since(self, login: str, since: Optional[datetime]) -> bool:
        if since is None:
            return False
        for review in self.pull_request.reviews():
            if review.author_handle() == login and review.submitted_at() >= since:
                return True
        for comment in self.pull_request.comments():
            if comment.author_handle() == login and comment.published_at() >= since:
                return True
        return False

    def _human_requested(self) -> Set[str]:
        """Reviewers a person asked for. SGTM's own review requests look the
        same on GitHub (asCodeOwner is false), so they are taken out; the
        choices recorded in `human_chosen_logins` stay whatever SGTM did with
        them afterwards."""
        on_github = set(self.pull_request.human_requested_reviewer_logins()) - set(
            self.state.sgtm_requested_logins
        )
        return on_github | set(self.state.human_chosen_logins)

    def _available(self, login: str) -> bool:
        return self._has_mapping(login) and not self._is_out_of_office(login)

    def _pool(self, evaluation: RequirementEvaluation) -> Set[str]:
        return self.inputs.resolve_pool(evaluation.owner_set) - {self.author}

    def _pick(
        self, evaluation: RequirementEvaluation, exclude: Optional[Set[str]] = None
    ) -> AssigneeChoice:
        return choose_assignee(
            pool=self._pool(evaluation),
            author=self.author,
            is_out_of_office=self._is_out_of_office,
            has_asana_mapping=self._has_mapping,
            human_requested_reviewers=self._human_requested(),
            engaged_logins=self._engaged_logins(),
            exclude=exclude,
            rng=self.inputs.rng,
        )

    # -- Asana field helpers ------------------------------------------------

    def _project_custom_fields(self) -> Dict[str, dict]:
        if self._project_fields is None:
            self._project_fields = {}
            project_id = config.SGTM_FEATURE__CODEOWNER_TASKS_PROJECT_ID
            if project_id:
                self._project_fields = {
                    cf["custom_field"]["name"]: cf["custom_field"]
                    for cf in asana_client.get_project_custom_fields(project_id)
                }
        return self._project_fields

    def _custom_fields(
        self, status: RequirementStatus, evaluation
    ) -> Dict[str, object]:
        fields = self._project_custom_fields()
        values: Dict[str, Optional[str]] = {
            FIELD_APPROVAL: status.value,
            FIELD_CODEOWNERS: ", ".join(evaluation.owner_set.display_names()),
            FIELD_PR_STATUS: asana_helpers._task_status_from_pull_request(
                self.pull_request
            ),
            FIELD_AUTHOR: self._gid(self.author),
            FIELD_BRANCH_NAME: self.pull_request.head_ref_name(),
        }
        data: Dict[str, object] = {}
        for name, value in values.items():
            custom_field = fields.get(name)
            if custom_field is None:
                continue
            resolved = asana_helpers.custom_field_value_for(custom_field, value)
            if resolved is not None:
                data[custom_field["gid"]] = resolved
        return data

    def _notes(self, evaluation: RequirementEvaluation, sub: SubtaskState) -> str:
        if sub.assignee:
            reason = sub.assignment_reason
        elif not evaluation.is_outstanding():
            reason = ""
        elif sub.manual:
            reason = "Assigned manually."
        else:
            reason = REASON_NOBODY_AVAILABLE
        return texts.subtask_description(
            self.pull_request,
            evaluation,
            self.inputs.parent_task_id,
            sub.assignee,
            reason,
        )

    def _comment(self, sub: SubtaskState, html: str) -> None:
        asana_client.add_comment(sub.task_id, html)

    def _set_assignee(self, sub: SubtaskState, login: Optional[str], reason: str):
        gid = self._gid(login) if login else self._gid(self.author)
        if gid:
            asana_client.update_task(sub.task_id, {"assignee": gid})
            asana_client.add_followers(sub.task_id, [gid])
        sub.assignee = login
        sub.assignment_reason = reason
        sub.assigned_at = self._now_iso()
        if login:
            self.state.remember_sgtm_requested(login)
            self.result.newly_assigned_logins.append(login)

    def _complete(self, sub: SubtaskState) -> None:
        if not sub.completed:
            asana_client.complete_task(sub.task_id)
            sub.completed = True

    def _reopen(self, sub: SubtaskState) -> None:
        if sub.completed:
            asana_client.reopen_task(sub.task_id)
            sub.completed = False
            # The assignee starts fresh: idleness counts from the revival.
            sub.assigned_at = self._now_iso()

    # -- creation -----------------------------------------------------------

    def _create(self, evaluation: RequirementEvaluation) -> None:
        key = evaluation.owner_set.key()
        if evaluation.is_outstanding():
            choice = self._pick(evaluation)
        else:
            # Already approved (or merged with bypass): record who approved for
            # the description, but ask nobody for anything.
            review = evaluation.approval_review()
            choice = AssigneeChoice(
                review.author_handle() if review is not None else None,
                REASON_ENGAGED if review is not None else "",
            )
        sub = SubtaskState(
            task_id="",
            owner_key=key,
            assignee=choice.login,
            assigned_at=self._now_iso(),
            assignment_reason=choice.reason if choice.login else "",
            status=evaluation.status.value,
            files=evaluation.requirement.all_files(),
            created_at=self._now_iso(),
        )
        assignee_gid = self._gid(choice.login) or self._gid(self.author)
        fields: Dict[str, object] = {
            "name": texts.subtask_name(
                self.pull_request, evaluation.owner_set, self.several_sets
            ),
        }
        if assignee_gid:
            fields["assignee"] = assignee_gid
        task_id = asana_client.create_subtask(self.inputs.parent_task_id, fields)
        sub.task_id = task_id
        # Recorded before anything else can fail, so a retry updates this task
        # instead of creating a second one.
        self.state.subtasks[key] = sub
        self.result.created_owner_keys.append(key)
        logger.info(f"Created codeowner subtask {task_id} for {key}")

        project_id = config.SGTM_FEATURE__CODEOWNER_TASKS_PROJECT_ID
        if project_id:
            asana_client.add_task_to_project(task_id, project_id)

        update: Dict[str, object] = {"html_notes": self._notes(evaluation, sub)}
        custom_fields = self._custom_fields(evaluation.status, evaluation)
        if custom_fields:
            update["custom_fields"] = custom_fields
        asana_client.update_task(task_id, update)
        sub.notes_hash = _hash(str(update["html_notes"]))
        sub.fields_hash = _hash(repr(sorted(custom_fields.items())))

        followers = [gid for gid in (assignee_gid, self._gid(self.author)) if gid]
        if followers:
            asana_client.add_followers(task_id, sorted(set(followers)))

        if evaluation.is_outstanding():
            if choice.login:
                self.state.remember_sgtm_requested(choice.login)
                self.result.newly_assigned_logins.append(choice.login)
            else:
                self._comment(sub, texts.comment_escalated(self.author))
        elif evaluation.status is RequirementStatus.APPROVED:
            review = evaluation.approval_review()
            if review is not None:
                self._comment(sub, texts.comment_approved(review, evaluation.owner_set))
            self._complete(sub)
        elif evaluation.status is RequirementStatus.MERGED_WITH_BYPASS:
            self._comment(sub, texts.comment_merged_with_bypass(None))

    # -- maintenance of an existing subtask ---------------------------------

    def _adopt_manual_reassignment(self, sub: SubtaskState) -> None:
        """Respect an assignee change made by hand in Asana."""
        try:
            task = asana_client.get_task(sub.task_id)
        except Exception as e:
            logger.warning(f"Could not read subtask {sub.task_id}: {e}")
            return
        assignee = task.get("assignee") if isinstance(task, dict) else None
        actual_gid = assignee.get("gid") if isinstance(assignee, dict) else None
        expected_gid = (
            self._gid(sub.assignee) if sub.assignee else self._gid(self.author)
        )
        if not isinstance(actual_gid, str) or actual_gid == expected_gid:
            return
        login = s3_client.get_github_handle_from_asana_domain_user_id(actual_gid)
        if login == self.author:
            return
        sub.manual = True
        sub.assigned_at = self._now_iso()
        sub.assignee = login
        sub.assignment_reason = "assigned by hand in Asana"
        if login:
            self.state.remember_human_chosen([login])
            self.result.newly_assigned_logins.append(login)
        logger.info(f"Adopted manual reassignment of {sub.task_id} to {login}")

    def _maintain_assignee(self, evaluation: RequirementEvaluation, sub: SubtaskState):
        pool = self._pool(evaluation)
        requested = (self._human_requested() & pool) - {self.author}

        # The author asked a specific codeowner who is available: follow that.
        if sub.assignee not in requested and not sub.manual:
            available = sorted(login for login in requested if self._available(login))
            if available:
                login = (self.inputs.rng or random.Random()).choice(available)
                self._set_assignee(sub, login, REASON_HUMAN_REQUESTED)
                self._comment(sub, texts.comment_reassigned_to_requested(login))
                return

        if sub.assignee:
            until = None
            try:
                until = self.inputs.out_of_office_until(sub.assignee)
            except Exception as e:
                logger.warning(f"Out-of-office lookup failed for {sub.assignee}: {e}")
            if until is not None:
                old = sub.assignee
                choice = self._pick(evaluation, exclude={old})
                sub.manual = False
                if choice.login:
                    self._set_assignee(sub, choice.login, choice.reason)
                    self._comment(
                        sub,
                        texts.comment_reassigned_out_of_office(
                            choice.login, old, until
                        ),
                    )
                else:
                    self._set_assignee(sub, None, "")
                    self._comment(sub, texts.comment_escalated(self.author))
                return

            # People a person chose are never replaced for idleness.
            if not sub.manual and sub.assignee not in requested:
                assigned_at = parse_iso(sub.assigned_at)
                engaged = self._engaged_since(sub.assignee, assigned_at)
                if assigned_at is not None and is_idle(
                    assigned_at,
                    self.inputs.now,
                    config.SGTM_FEATURE__CODEOWNER_TASKS_IDLE_BUSINESS_DAYS,
                    engaged,
                ):
                    choice = self._pick(evaluation, exclude={sub.assignee})
                    if choice.login:
                        days = business_days_between(assigned_at, self.inputs.now)
                        self._set_assignee(sub, choice.login, choice.reason)
                        self._comment(
                            sub, texts.comment_reassigned_idle(choice.login, days)
                        )
            return

        # Escalated to the author earlier: try again now.
        if not sub.manual:
            choice = self._pick(evaluation)
            if choice.login:
                self._set_assignee(sub, choice.login, choice.reason)
                self._comment(
                    sub,
                    texts.comment_assigned_after_escalation(
                        choice.login, choice.reason
                    ),
                )

    def _apply_status(self, evaluation: RequirementEvaluation, sub: SubtaskState):
        previous = RequirementStatus(sub.status) if sub.status else None
        new = evaluation.status
        if new is previous:
            if sub.completed and evaluation.is_outstanding():
                # Completed when the PR was closed; the PR is open again.
                self._reopen(sub)
                self._comment(sub, texts.comment_pr_reopened())
            return
        if new is RequirementStatus.APPROVED:
            review = evaluation.approval_review()
            if review is not None:
                if previous is RequirementStatus.MERGED_WITH_BYPASS:
                    self._comment(sub, texts.comment_approved_after_merge(review))
                else:
                    self._comment(
                        sub, texts.comment_approved(review, evaluation.owner_set)
                    )
            self._complete(sub)
        elif new in (RequirementStatus.NEEDED, RequirementStatus.APPROVAL_STALE):
            if previous is RequirementStatus.NO_LONGER_REQUIRED:
                self._reopen(sub)
                self._comment(
                    sub,
                    texts.comment_required_again(evaluation.requirement.all_files()),
                )
            elif previous is RequirementStatus.APPROVED:
                self._reopen(sub)
                stale = evaluation.stale_review()
                self._comment(
                    sub,
                    texts.comment_approval_dismissed(
                        stale.author_handle() if stale else None,
                        self.pull_request.head_ref_oid(),
                    ),
                )
            else:
                self._reopen(sub)
        elif new is RequirementStatus.CHANGES_REQUESTED:
            self._reopen(sub)
            review = evaluation.changes_requested_review()
            if review is not None:
                self._comment(
                    sub, texts.comment_changes_requested(review, sub.assignee)
                )
        elif new is RequirementStatus.MERGED_WITH_BYPASS:
            self._reopen(sub)
            self._comment(sub, texts.comment_merged_with_bypass(None))
        sub.status = new.value

    def _update_task_content(
        self, evaluation: RequirementEvaluation, sub: SubtaskState
    ):
        notes = self._notes(evaluation, sub)
        update: Dict[str, object] = {}
        notes_hash = _hash(notes)
        if notes_hash != sub.notes_hash:
            update["html_notes"] = notes
            update["name"] = texts.subtask_name(
                self.pull_request, evaluation.owner_set, self.several_sets
            )
        custom_fields = self._custom_fields(evaluation.status, evaluation)
        fields_hash = _hash(repr(sorted(custom_fields.items())))
        if custom_fields and fields_hash != sub.fields_hash:
            update["custom_fields"] = custom_fields
        if update:
            asana_client.update_task(sub.task_id, update)
            sub.notes_hash = notes_hash
            sub.fields_hash = fields_hash
        sub.files = evaluation.requirement.all_files()

    def _update_existing(self, evaluation: RequirementEvaluation, sub: SubtaskState):
        closed_unmerged = self.pull_request.closed() and not self.pull_request.merged()
        if closed_unmerged:
            if not sub.completed:
                self._comment(sub, texts.comment_closed_unmerged())
                self._complete(sub)
            return
        self._adopt_manual_reassignment(sub)
        self._apply_status(evaluation, sub)
        if evaluation.is_outstanding():
            self._maintain_assignee(evaluation, sub)
        self._update_task_content(evaluation, sub)

    def _retire_orphans(self, current_keys: Set[str]) -> None:
        for key, sub in self.state.subtasks.items():
            if (
                key in current_keys
                or sub.status == RequirementStatus.NO_LONGER_REQUIRED.value
            ):
                continue
            if self.pull_request.closed() and not self.pull_request.merged():
                if not sub.completed:
                    self._comment(sub, texts.comment_closed_unmerged())
                    self._complete(sub)
                continue
            self._comment(sub, texts.comment_no_longer_required(sub.files))
            fields = self._project_custom_fields()
            approval_field = fields.get(FIELD_APPROVAL)
            if approval_field is not None:
                value = asana_helpers.custom_field_value_for(
                    approval_field, RequirementStatus.NO_LONGER_REQUIRED.value
                )
                if value is not None:
                    asana_client.update_task(
                        sub.task_id, {"custom_fields": {approval_field["gid"]: value}}
                    )
            self._complete(sub)
            sub.status = RequirementStatus.NO_LONGER_REQUIRED.value

    # -- entry point --------------------------------------------------------

    def run(self) -> SubtaskSyncResult:
        if not self.state.tasks_requested:
            return self.result
        current_keys: Set[str] = set()
        closed_unmerged = self.pull_request.closed() and not self.pull_request.merged()
        for evaluation in self.summary.evaluations:
            key = evaluation.owner_set.key()
            current_keys.add(key)
            sub = self.state.subtasks.get(key)
            try:
                if sub is None:
                    if (
                        closed_unmerged
                        or evaluation.status is RequirementStatus.NO_LONGER_REQUIRED
                    ):
                        continue
                    self._create(evaluation)
                else:
                    self._update_existing(evaluation, sub)
            except Exception as e:
                # One broken subtask (deleted in Asana, say) must not stop the
                # others from being maintained.
                logger.error(
                    f"Codeowner subtask sync failed for {key}: {e}", exc_info=True
                )
        self._retire_orphans(current_keys)
        return self.result


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def sync_subtasks(inputs: SubtaskSyncInputs) -> SubtaskSyncResult:
    """Bring the PR's codeowner subtasks in line with `inputs.summary`.

    Does nothing until the author has added the label (state.tasks_requested).
    Mutates `inputs.state`; the caller persists it.
    """
    return _Sync(inputs).run()
