from typing import Optional  # Python 3.8 or higher: Literal, TypedDict
from typing_extensions import Literal, TypedDict

HTTP_STATUS = Literal["200", "400", "401", "500", "501"]


class HttpResponseDict(TypedDict):
    statusCode: str
    body: Optional[str]


class HttpResponse(object):
    def __init__(self, status_code: HTTP_STATUS, body: Optional[str] = None):
        self.status_code = status_code
        self.body = body

    def to_dict(self) -> HttpResponseDict:
        return {"statusCode": self.status_code, "body": self.body}
