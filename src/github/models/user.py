from typing import Optional, Dict, Any
import copy


class User(object):
    def __init__(self, raw_user: Dict[str, Any]):
        if "login" not in raw_user or not raw_user["login"].strip():
            raise ValueError("User must have a login")
        self.__raw = copy.deepcopy(raw_user)

    def id(self) -> str:
        return self.__raw["id"]

    def login(self) -> str:
        return self.__raw["login"]

    def name(self) -> Optional[str]:
        if "name" not in self.__raw:
            return None
        return self.__raw["name"]

    def to_raw(self) -> Dict[str, Any]:
        return copy.deepcopy(self.__raw)
