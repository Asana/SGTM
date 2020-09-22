from typing import Dict, Any, Optional
import copy


class Commit(object):
    BUILD_SUCCESSFUL = "SUCCESS"
    BUILD_PENDING = "PENDING"
    BUILD_FAILED = "FAILURE"

    def __init__(self, raw_commit: Dict[str, Any]):
        self._raw = copy.deepcopy(raw_commit)

    def status(self) -> Optional[str]:
        return self._raw["commit"].get("status", {}).get("state", None)

    def node_id(self) -> str:
        return self._raw["commit"]["node_id"]

    def to_raw(self) -> Dict[str, Any]:
        return copy.deepcopy(self._raw)
