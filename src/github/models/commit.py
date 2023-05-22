from typing import Dict, Any, Optional, List
import copy

from .check_suite import CheckSuite


class Commit(object):
    BUILD_SUCCESSFUL = "SUCCESS"
    BUILD_PENDING = "PENDING"
    BUILD_FAILED = "FAILURE"

    def __init__(self, raw_commit: Dict[str, Any]):
        self._raw = copy.deepcopy(raw_commit)

    # A commit's status can be None while the logic to start tests runs right after committing.
    def status(self) -> Optional[str]:
        status = self._raw["commit"].get("statusCheckRollup")

        if status is None:
            return None
        else:
            return status.get("state", None)
        
    def check_suites(self) -> List[CheckSuite]:
        return [CheckSuite(raw_check_suite) for raw_check_suite in self._raw["commit"]["checkSuites"]["nodes"]]

    def node_id(self) -> str:
        return self._raw["commit"]["node_id"]

    def to_raw(self) -> Dict[str, Any]:
        return copy.deepcopy(self._raw)
