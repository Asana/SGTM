from datetime import datetime
from typing import Dict, Any
from src.utils import parse_date_string
from .user import User

import copy


class Comment(object):
    def __init__(self, raw_comment: Dict[str, Any]):
        self._raw = copy.deepcopy(raw_comment)

    def id(self) -> str:
        return self._raw["id"]

    def published_at(self) -> datetime:
        return parse_date_string(self._raw["publishedAt"])

    def body(self) -> str:
        return self._raw["body"]

    def author_handle(self) -> str:
        return self.author().login()

    def author(self) -> User:
        return User(self._raw["author"])

    def to_raw(self) -> Dict[str, Any]:
        return copy.deepcopy(self._raw)

    def url(self) -> str:
        return self._raw["url"]


class IssueComment(Comment):
    pass


class PullRequestReviewComment(Comment):
    def raw_review(self) -> dict:
        return self._raw["pullRequestReview"]


def comment_factory(raw: Dict[str, Any]) -> Comment:
    if raw["__typename"] == "IssueComment":
        return IssueComment(raw)
    elif raw["__typename"] == "PullRequestReviewComment":
        return PullRequestReviewComment(raw)
    else:
        raise Exception(f"Unexpected type found: {raw['__typename']}")
