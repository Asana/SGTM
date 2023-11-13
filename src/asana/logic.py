from src.github.models import PullRequest
from src.github.helpers import pull_request_has_label
from enum import Enum, unique
from src.config import (
    SGTM_FEATURE__AUTOCOMPLETE_ENABLED,
    SGTM_FEATURE__TASK_ASSIGNEE_IS_ALWAYS_PR_AUTHOR,
)


@unique
class AutocompleteLabel(Enum):
    COMPLETE_ON_MERGE = "complete tasks on merge"


@unique
class TaskAssigneeLabel(Enum):
    PR_AUTHOR = "task assignee is always pr author"


def should_autocomplete_tasks_on_merge(pull_request: PullRequest) -> bool:
    return (
        SGTM_FEATURE__AUTOCOMPLETE_ENABLED
        and pull_request.merged()
        and pull_request_has_label(
            pull_request, AutocompleteLabel.COMPLETE_ON_MERGE.value
        )
    )


def should_set_task_owner_to_pr_author(pull_request: PullRequest) -> bool:
    return SGTM_FEATURE__TASK_ASSIGNEE_IS_ALWAYS_PR_AUTHOR and pull_request_has_label(
        pull_request, TaskAssigneeLabel.PR_AUTHOR.value
    )
