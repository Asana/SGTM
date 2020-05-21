# @CyclicDependencyBetweenCommentAndReview
from __future__ import annotations

from typing import Dict, Any, List
from datetime import datetime
from enum import Enum, unique

from src.utils import parse_date_string
from .user import User
import copy
from . import pull_request_review_comment


@unique
class ReviewState(Enum):
    """https://developer.github.com/v4/reference/enum/pullrequestreviewstate/"""

    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    COMMENTED = "COMMENTED"
    DISMISSED = "DISMISSED"


class Review(object):
    def __init__(self, raw_review: Dict[str, Any]):
        self._raw = copy.deepcopy(raw_review)

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

    def comments(self) -> List[pull_request_review_comment.PullRequestReviewComment]:
        return [
            pull_request_review_comment.PullRequestReviewComment(comment)
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
        This is true for inline comments without a review (Github still creates a review object)
        XCXC: Clarify this.
        XCXC: unit test this?
        """
        return self.state() == Review.STATE_COMMENTED and not self.body()
