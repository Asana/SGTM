from datetime import datetime
from typing import Dict, Any
from src.utils import parse_date_string

import copy


class CheckRun(object):
    def __init__(self, raw_check_run: Dict[str, Any]):
        self._raw = copy.deepcopy(raw_check_run)

    def completed_at(self) -> datetime:
        return parse_date_string(self._raw["completedAt"])

    def database_id(self) -> int:
        return self._raw["databaseId"]

    def to_raw(self) -> Dict[str, Any]:
        return copy.deepcopy(self._raw)
