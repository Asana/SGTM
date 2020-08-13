from typing import Dict, Any
import copy


class Label(object):
    def __init__(self, raw_label: Dict[str, Any]):
        self._raw = copy.deepcopy(raw_label)

    def name(self) -> str:
        return self._raw["name"]

    def to_raw(self) -> Dict[str, Any]:
        return copy.deepcopy(self._raw)
