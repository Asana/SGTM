from datetime import datetime
from typing import Dict, Any, Optional, List
import copy

from src.utils import parse_date_string
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
        return [
            CheckSuite(raw_check_suite)
            for raw_check_suite in self._raw["commit"]["checkSuites"]["nodes"]
        ]

    def node_id(self) -> str:
        return self._raw["commit"]["node_id"]

    def oid(self) -> Optional[str]:
        """The commit sha, when the query included it."""
        return self._raw["commit"].get("oid")

    def committed_date(self) -> Optional[datetime]:
        committed_date = self._raw["commit"].get("committedDate")
        if committed_date is None:
            return None
        return parse_date_string(committed_date)

    def to_raw(self) -> Dict[str, Any]:
        return copy.deepcopy(self._raw)
