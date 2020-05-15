from typing import Dict, Any, List
from datetime import datetime
from src.utils import parse_date_string
from .user import User
import copy
from .issue_comment import IssueComment


class Review(object):
    STATE_APPROVED = "APPROVED"
    STATE_CHANGES_REQUESTED = "CHANGES_REQUESTED"
    STATE_COMMENTED = "COMMENTED"
    STATE_DISMISSED = "DISMISSED"

    def __init__(self, raw_review: Dict[str, Any]):
        self._raw = copy.deepcopy(raw_review)

    def id(self) -> str:
        return self._raw["id"]

    def submitted_at(self) -> datetime:
        return parse_date_string(self._raw["submittedAt"])

    def state(self) -> str:
        return self._raw["state"]

    def is_approval_or_changes_requested(self) -> bool:
        return self.state() in (self.STATE_APPROVED, self.STATE_CHANGES_REQUESTED)

    def is_approval(self) -> bool:
        return self.state() == self.STATE_APPROVED

    def body(self) -> str:
        return self._raw["body"]

    def comments(self) -> List[IssueComment]:
        return [
            IssueComment(comment)
            for comment in self._raw.get("comments", {}).get("nodes", [])
        ]

    def author(self) -> User:
        return User(self._raw["author"])

    def author_handle(self) -> str:
        return self.author().login()

    def to_raw(self) -> Dict[str, Any]:
        return copy.deepcopy(self._raw)

    def url(self) -> str:
        return self._raw["url"]
