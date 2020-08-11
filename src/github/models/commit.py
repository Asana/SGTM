from typing import Dict, Any
import copy


class Commit(object):
    BUILD_SUCCESSFUL = "SUCCESS"
    BUILD_PENDING = "PENDING"
    BUILD_FAILED = "FAILURE"

    def __init__(self, raw_commit: Dict[str, Any]):
        self.__raw = copy.deepcopy(raw_commit)

    def status(self) -> str:
        return self.__raw["commit"]["status"]["state"]

    def node_id(self) -> str:
        return self.__raw["commit"]["node_id"]

    def to_raw(self) -> Dict[str, Any]:
        return copy.deepcopy(self.__raw)
