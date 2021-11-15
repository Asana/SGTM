from typing import Optional, Dict, Any
import copy


class Subtask(object):
    def __init__(self, raw_subtask: Dict[str, Any]):
        self._raw = copy.deepcopy(raw_subtask)

    def id(self) -> str:
        return self._raw["gid"]

    def completed(self) -> bool:
        return self._raw["completed"]

    def assignee_id(self) -> Optional[str]:
        if self._raw["assignee"] is None:
            return None

        return self._raw["assignee"]["gid"]
