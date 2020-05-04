from typing import Dict, Any
import copy


class HttpResponse(object):
    def __init__(self, raw_http_response: Dict[str, Any]):
        self.__raw = copy.deepcopy(raw_http_response)

    def status_code(self) -> str:
        return self.__raw["statusCode"]

    def body(self) -> Any:
        return self.__raw["body"]

    def to_raw(self) -> Dict[str, Any]:
        return copy.deepcopy(self.__raw)
