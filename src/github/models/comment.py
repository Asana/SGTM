from datetime import datetime
from typing import Dict, Any
from src.utils import parse_date_string
from .user import User
from .review import Review
import copy


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

    def review(self) -> Review:
        # XCXC: Make a separate type for IssueComment and PullRequestReviewComment
        # only the latter would implement this.
        return Review(self.__raw['pullRequestReview'])
