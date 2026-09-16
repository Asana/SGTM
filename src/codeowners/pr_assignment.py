"""Who the pull request is assigned to while codeowner approvals are pending.

The GitHub assignee is the "ball": SGTM mirrors it onto the Asana PR task.
Without this feature every approval or request for changes hands the ball to
the author. With codeowner tasks requested for a PR that touches codeowned
files, the rules become:

* Changes requested (by anyone): back to the author.
* Approval: to the author once the primary review is in and every codeowner
  requirement is satisfied; to an outstanding codeowner subtask's assignee
  while the primary review is in but codeowner approvals are still missing;
  and, when a codeowner approved before the primary reviewer did, to a
  reviewer the author chose who has not reviewed yet.
* Adding the label moves the PR to a codeowner only if the primary review is
  already in.
* Anything else (pushes, comments) leaves the assignee alone, except that a
  codeowner SGTM assigned who has since been replaced on the subtask hands
  over to the replacement.

A codeowner a person assigned by hand keeps the PR; SGTM only moves an
assignee it set itself, or the author.
"""
from typing import Optional

from src.github.models import PullRequest, Review

from .state import CodeownerState, SubtaskState
from .status import CodeownerSummary, has_primary_review

TRIGGER_REVIEW = "review"
TRIGGER_TASKS_CREATED = "tasks_created"
TRIGGER_SYNC = "sync"


def choose_outstanding_subtask(
    summary: CodeownerSummary, state: CodeownerState
) -> Optional[SubtaskState]:
    """The outstanding subtask whose assignee should hold the PR: one assigned
    to a reviewer the author chose first, then any with an assignee over one
    escalated to the author, then the one owning the fewest changed files,
    then the earliest created."""
    outstanding = {e.owner_set.key(): e for e in summary.outstanding()}
    ranked = []
    for key, sub in state.subtasks.items():
        evaluation = outstanding.get(key)
        if evaluation is None:
            continue
        chosen_by_author = bool(sub.assignee) and sub.assignee in (
            state.human_chosen_logins
        )
        ranked.append(
            (
                0 if chosen_by_author else 1,
                0 if sub.assignee else 1,
                len(evaluation.requirement.all_files()),
                sub.created_at or "",
                key,
            )
        )
    if not ranked:
        return None
    return state.subtasks[min(ranked)[-1]]


def _decisively_reviewed(pull_request: PullRequest) -> set:
    return {
        review.author_handle()
        for review in pull_request.reviews()
        if review.is_approval_or_changes_requested()
    }


def decide_pull_request_assignee(
    pull_request: PullRequest,
    summary: CodeownerSummary,
    state: CodeownerState,
    trigger: str,
    review: Optional[Review] = None,
) -> Optional[str]:
    """The login the PR should be assigned to now, or None to leave it as is.

    Returns None as well when the feature's rules do not apply (no codeowned
    files, or tasks were never requested); the caller then falls back to
    SGTM's plain behaviour.
    """
    if not summary.has_codeowned_files() or not state.tasks_requested:
        return None
    author = pull_request.author_handle()
    current = pull_request.assignee().login

    if trigger == TRIGGER_REVIEW:
        if review is None or not review.is_approval_or_changes_requested():
            return None
        if review.is_changes_requested():
            return _move(current, author)
        if pull_request.closed():
            # Post-merge approvals: nothing left to route, back to the author.
            return _move(current, author)

    primary = has_primary_review(pull_request, summary)
    outstanding_keys = {e.owner_set.key() for e in summary.outstanding()}
    outstanding_assignees = {
        sub.assignee
        for key, sub in state.subtasks.items()
        if sub.assignee and key in outstanding_keys
    }
    # SGTM only moves an assignee it set itself (the author included); anyone
    # else was put in charge by a person.
    set_by_sgtm = current == state.sgtm_assigned_login

    if not primary:
        if trigger != TRIGGER_REVIEW:
            return None
        # A codeowner approved first: hand the PR to a reviewer the author chose
        # who has not weighed in yet, so the primary review happens next.
        reviewed = _decisively_reviewed(pull_request)
        for login in state.human_chosen_logins:
            if login != author and login not in reviewed:
                return _move(current, login)
        return None

    if not outstanding_keys:
        if trigger == TRIGGER_REVIEW or set_by_sgtm:
            return _move(current, author)
        return None

    target_sub = choose_outstanding_subtask(summary, state)
    target = (target_sub.assignee if target_sub is not None else None) or author

    if trigger == TRIGGER_SYNC:
        # Only follow a subtask reassignment SGTM made (out of office, idle).
        if set_by_sgtm and current not in outstanding_assignees:
            return _move(current, target)
        return None

    if current in outstanding_assignees:
        return None
    if (
        current != author
        and current in summary.codeowner_logins
        and not set_by_sgtm
        and current not in _decisively_reviewed(pull_request)
    ):
        # A person put a codeowner in charge by hand and that codeowner has
        # not reviewed yet: respect it.
        return None
    return _move(current, target)


def _move(current: str, target: str) -> Optional[str]:
    return target if target != current else None
