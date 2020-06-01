from __future__ import annotations

from typing import Dict, Any, List
from datetime import datetime
from enum import Enum, unique

from src.utils import parse_date_string
from .user import User
import copy
from .pull_request_review_comment import PullRequestReviewComment


@unique
class ReviewState(Enum):
    """https://developer.github.com/v4/reference/enum/pullrequestreviewstate/"""

    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    COMMENTED = "COMMENTED"
    DISMISSED = "DISMISSED"
    DEFAULT = "DEFAULT"


class Review(object):
    def __init__(self, raw_review: Dict[str, Any]):
        self._raw = copy.deepcopy(raw_review)

    @classmethod
    def from_comment(cls, comment: PullRequestReviewComment) -> Review:
        return cls(comment.raw_review())

    def id(self) -> str:
        return self._raw["id"]

    def submitted_at(self) -> datetime:
        return parse_date_string(self._raw["submittedAt"])

    def state(self) -> ReviewState:
        return ReviewState(self._raw["state"])

    def is_approval_or_changes_requested(self) -> bool:
        return self.state() in (ReviewState.APPROVED, ReviewState.CHANGES_REQUESTED)

    def is_approval(self) -> bool:
        return self.state() == ReviewState.APPROVED

    def body(self) -> str:
        return self._raw["body"]

    def comments(self) -> List[PullRequestReviewComment]:
        return [
            PullRequestReviewComment(comment)
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

    def is_just_comments(self) -> bool:
        """Return true if this review is not a meaningful state and doesn't contain a body.
        For inline comments/replies without a body, Github still creates a review object.
        This object is basically empty so in some cases we process it differently.
        """
        return self.state() == ReviewState.COMMENTED and not self.body()
