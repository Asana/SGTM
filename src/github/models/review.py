from datetime import datetime
from typing import List, Dict, Any
from src.logger import logger
from src.utils import parse_date_string
from .comment import Comment
from .user import User
import copy


class Review(object):
    STATE_APPROVED = "APPROVED"
    STATE_CHANGES_REQUESTED = "CHANGES_REQUESTED"
    STATE_COMMENTED = "COMMENTED"
    STATE_DISMISSED = "DISMISSED"

    def __init__(self, raw_review: Dict[str, Any]):
        self.__raw = copy.deepcopy(raw_review)

    def id(self) -> str:
        return self.__raw["id"]

    def submitted_at(self) -> datetime:
        return parse_date_string(self.__raw["submittedAt"])

    def state(self) -> str:
        return self.__raw["state"]

    def is_approval_or_changes_requested(self) -> bool:
        return self.state() in (self.STATE_APPROVED, self.STATE_CHANGES_REQUESTED)

    def is_approval(self) -> bool:
        return self.state() == self.STATE_APPROVED

    def body(self) -> str:
        return self.__raw["body"]

    def comments(self) -> List[Comment]:
        return [
            Comment(comment)
            for comment in self.__raw.get("comments", {}).get("nodes", [])
        ]

    def author(self) -> User:
        return User(self.__raw["author"])

    def author_handle(self) -> str:
        return self.author().login()

    def to_raw(self) -> Dict[str, Any]:
        return copy.deepcopy(self.__raw)

    def url(self) -> str:
        return self.__raw['url']
