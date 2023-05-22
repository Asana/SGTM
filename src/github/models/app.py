from typing import Dict, Any

import copy


class App(object):
    def __init__(self, raw_app: Dict[str, Any]):
        self._raw = copy.deepcopy(raw_app)

    def name(self) -> str:
        return self._raw["name"]

    def node_id(self) -> str:
        return self._raw["id"]
    
    def app_id(self):
        return self._raw["databaseId"]
    
    def to_raw(self) -> Dict[str, Any]:
        return copy.deepcopy(self._raw)
