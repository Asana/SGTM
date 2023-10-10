from typing import Dict, Any, Optional, List
import copy

from .status_check_rollup_context import (
    StatusCheckRollupContext,
    StatusCheckRollupContextState,
    status_check_rollup_context_factory,
)
from src.config import SGTM_FEATURE__IGNORED_STATUS_CHECK_CONTEXTS
from src.utils import memoize


class Commit(object):
    BUILD_SUCCESSFUL = "SUCCESS"
    BUILD_PENDING = "PENDING"
    BUILD_FAILED = "FAILURE"

    def __init__(self, raw_commit: Dict[str, Any]):
        self._raw = copy.deepcopy(raw_commit)

    # # A commit's status can be None while the logic to start tests runs right after committing.
    # def status(self) -> Optional[str]:
    #     status = self._raw["commit"].get("statusCheckRollup")

    #     if status is None:
    #         return None
    #     else:
    #         return status.get("state", None)

    def status_check_rollup_contexts(self) -> List[StatusCheckRollupContext]:
        return [
            status_check_rollup_context_factory(raw_status)
            for raw_status in self._raw["commit"]["statusCheckRollup"]["contexts"]
        ]

    @memoize
    def status(self) -> Optional[StatusCheckRollupContextState]:
        most_severe_status = max(
            (
                status
                for status in self.status_check_rollup_contexts()
                if status.name() not in SGTM_FEATURE__IGNORED_STATUS_CHECK_CONTEXTS
            ),
            key=lambda status: status.state(),
            default=None,
        )
        return most_severe_status.state() if most_severe_status is not None else None

    def node_id(self) -> str:
        return self._raw["commit"]["node_id"]

    def to_raw(self) -> Dict[str, Any]:
        return copy.deepcopy(self._raw)
