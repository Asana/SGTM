from datetime import datetime
from typing import Dict, Any, List
from src.utils import parse_date_string
from .user import User
# from .review import Review
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

    def comments(self):
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
        return self.__raw["url"]


class Comment(object):
    def __init__(self, raw_comment: Dict[str, Any]):
        self.__raw = copy.deepcopy(raw_comment)

    def id(self) -> str:
        return self.__raw["id"]

    def published_at(self) -> datetime:
        return parse_date_string(self.__raw["publishedAt"])

    def body(self) -> str:
        return self.__raw["body"]

    def author_handle(self) -> str:
        return self.author().login()

    def author(self) -> User:
        return User(self.__raw["author"])

    def to_raw(self) -> Dict[str, Any]:
        return copy.deepcopy(self.__raw)

    def url(self) -> str:
        return self.__raw["url"]

    def review(self):
        # XCXC: Make a separate type for IssueComment and PullRequestReviewComment
        # only the latter would implement this.
        return Review(self.__raw['pullRequestReview'])
