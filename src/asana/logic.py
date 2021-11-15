from src.github.models import Review, PullRequest
from src.github.helpers import pull_request_has_label
from enum import Enum, unique
from src.config import SGTM_FEATURE__AUTOCOMPLETE_ENABLED


@unique
class AutocompleteLabel(Enum):
    COMPLETE_ON_MERGE = "complete tasks on merge"


def should_autocomplete_tasks_on_merge(pull_request: PullRequest) -> bool:

    return (
        SGTM_FEATURE__AUTOCOMPLETE_ENABLED
        and pull_request.merged()
        and pull_request_has_label(
            pull_request, AutocompleteLabel.COMPLETE_ON_MERGE.value
        )
    )


def should_complete_subtask_after_review(pull_request: PullRequest, review: Review) -> bool:
    """Determine if a subtask of PR task should be completed based on given review."""
    if review.author_handle() not in pull_request.assignees():
        return True
    else:
        return review.is_approval_or_changes_requested()


def should_complete_subtask_after_pr_merge(pull_request: PullRequest, task_assignee: str):
    """Determine if a subtask of PR task should be completed on PR merge."""
    pass
