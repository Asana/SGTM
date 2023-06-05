from datetime import datetime
from typing import Dict, Any
from src.utils import parse_date_string
from enum import Enum, unique

import copy


@unique
class CheckConclusionState(Enum):
    """https://docs.github.com/en/graphql/reference/enums#checkconclusionstate"""

    ACTION_REQUIRED = "ACTION_REQUIRED"
    CANCELLED = "CANCELLED"
    FAILURE = "FAILURE"
    NEUTRAL = "NEUTRAL"
    SKIPPED = "SKIPPED"
    STALE = "STALE"
    STARTUP_FAILURE = "STARTUP_FAILURE"
    SUCCESS = "SUCCESS"
    TIMED_OUT = "TIMED_OUT"
    NONE = "NONE"


class CheckRun(object):
    def __init__(self, raw_check_run: Dict[str, Any]):
        self._raw = copy.deepcopy(raw_check_run)

    def id(self) -> str:
        return self._raw["id"]

    def completed_at(self) -> datetime:
        return parse_date_string(self._raw["completedAt"])

    def is_required(self) -> bool:
        return self._raw["isRequired"]

    def name(self) -> str:
        return self._raw["name"]

    def status(self) -> str:
        return self._raw["status"]

    def url(self) -> str:
        return self._raw["url"]

    def database_id(self) -> int:
        return self._raw["databaseId"]

    def conclusion(self) -> CheckConclusionState:
        return CheckConclusionState(self._raw["conclusion"])

    def to_raw(self) -> Dict[str, Any]:
        return copy.deepcopy(self._raw)
