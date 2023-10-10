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

    NEUTRAL = 0  # check conclusion state
    SKIPPED = 1  # check conclusion state
    SUCCESS = 2  # both
    EXPECTED = 3  # status state
    PENDING = 4  # status state
    STALE = 5  # check conclusion state
    CANCELLED = 6  # check conclusion state
    ACTION_REQUIRED = 7  # check conclusion state
    STARTUP_FAILURE = 8  # check conclusion state
    TIMED_OUT = 9  # check conclusion state
    ERROR = 10  # status state
    FAILURE = 11  # both

    def __str__(self):
        return f"{self.__class__.__name__}.{self.name}"

    @classmethod
    def _missing_(cls, value):
        if type(value) is str:
            if value in dir(cls):
                return cls[value]

        raise ValueError("%r is not a valid %s" % (value, cls.__name__))


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


class StatusContext(StatusCheckRollupContext):
    def name(self) -> str:
        return self._raw["context"]

    def completed_at(self) -> datetime:
        return parse_date_string(self._raw["createdAt"])

    def state(self) -> StatusCheckRollupContextState:
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
