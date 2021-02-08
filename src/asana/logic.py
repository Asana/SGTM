from src.github.models import PullRequest
from src.github.helpers import pull_request_has_label
from enum import Enum, unique
import os


@unique
class AutocompleteLabel(Enum):
    COMPLETE_ON_MERGE = "complete tasks on merge"


def should_autocomplete_tasks_on_merge(pull_request: PullRequest):
    return (
        _is_autocomplete_feature_enabled()
        and pull_request.merged()
        and pull_request_has_label(
            pull_request, AutocompleteLabel.COMPLETE_ON_MERGE.value
        )
    )


def _is_autocomplete_feature_enabled():
    return os.getenv("SGTM_FEATURE__AUTOCOMPLETE_ENABLED") == "true"
