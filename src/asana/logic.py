from src.github.models import PullRequest
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
