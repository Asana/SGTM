from src.github.models import PullRequest
from enum import Enum, unique
from src.config import (
    SGTM_FEATURE__AUTOCOMPLETE_ENABLED,
    SGTM_FEATURE__ALLOW_PERSISTENT_TASK_ASSIGNEE,
)


@unique
class AutocompleteLabel(Enum):
    COMPLETE_ON_MERGE = "complete tasks on merge"


@unique
class TaskAssigneeLabel(Enum):
    PERSISTENT = "persistent task assignee"


def should_autocomplete_tasks_on_merge(pull_request: PullRequest) -> bool:
    return (
        SGTM_FEATURE__AUTOCOMPLETE_ENABLED
        and pull_request.merged()
        and pull_request.has_label(AutocompleteLabel.COMPLETE_ON_MERGE.value)
    )


def should_set_task_owner_to_pr_author(pull_request: PullRequest) -> bool:
    return SGTM_FEATURE__ALLOW_PERSISTENT_TASK_ASSIGNEE and pull_request.has_label(
        TaskAssigneeLabel.PERSISTENT.value
    )
