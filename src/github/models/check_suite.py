from typing import Dict, Any, List

from .check_run import CheckRun
import copy


class CheckSuite(object):
    def __init__(self, raw_check_suite: Dict[str, Any]):
        self._raw = copy.deepcopy(raw_check_suite)

    def check_runs(self) -> List[CheckRun]:
        return [
            CheckRun(raw_check_run) for raw_check_run in self._raw["checkRuns"]["nodes"]
        ]

    def to_raw(self) -> Dict[str, Any]:
        return copy.deepcopy(self._raw)
