from datetime import datetime
from typing import Dict, Any, Optional
from src.utils import parse_date_string
from enum import IntEnum, unique
import copy


@unique
class StatusCheckRollupContextState(IntEnum):
    """
    A combined status enum for status check states and check run conclusions. Ordered by severity.
    StatusStates: https://docs.github.com/en/graphql/reference/enums#statusstate
    CheckConclusionStates: https://docs.github.com/en/graphql/reference/enums#checkconclusionstate
    """

    SUCCESS = 0  # both
    PENDING = 1  # status state
    EXPECTED = 2  # status state
    SKIPPED = 3  # check conclusion state
    NEUTRAL = 4  # check conclusion state
    STALE = 5  # check conclusion state
    CANCELLED = 6  # check conclusion state
    ACTION_REQUIRED = 7  # check conclusion state
    STARTUP_FAILURE = 8  # check conclusion state
    TIMED_OUT = 9  # check conclusion state
    ERROR = 10  # status state
    FAILURE = 11  # both


class StatusCheckRollupContext(object):
    def __init__(self, raw_json: Dict[str, Any]):
        self._raw = copy.deepcopy(raw_json)

    def completed_at(self) -> datetime:
        raise NotImplementedError()

    def name(self) -> str:
        raise NotImplementedError()

    def state(self) -> StatusCheckRollupContextState:
        raise NotImplementedError()

    def is_required(self) -> bool:
        raise self._raw["isRequired"]

    def database_id(self) -> Optional[int]:
        return None

    def to_raw(self) -> Dict[str, Any]:
        return copy.deepcopy(self._raw)


class CheckRun(StatusCheckRollupContext):
    def completed_at(self) -> datetime:
        return parse_date_string(self._raw["completedAt"])

    def database_id(self) -> Optional[int]:
        return self._raw["databaseId"]

    def name(self) -> str:
        return self._raw["name"]

    def state(self) -> StatusCheckRollupContextState:
        return StatusCheckRollupContextState(self._raw["conclusion"])


class StatusContext(object):
    def name(self) -> str:
        return self._raw["context"]

    def completed_at(self) -> datetime:
        return parse_date_string(self._raw["createdAt"])

    def state(self) -> str:
        return StatusCheckRollupContextState(self._raw["state"])


def status_check_rollup_context_factory(
    raw: Dict[str, Any]
) -> StatusCheckRollupContext:
    if raw["__typename"] == "StatusContext":
        return StatusContext(raw)
    elif raw["__typename"] == "CheckRun":
        return CheckRun(raw)
    else:
        raise Exception(f"Unexpected type found: {raw['__typename']}")
