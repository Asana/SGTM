from __future__ import annotations

from .comment import Comment
from . import review

class PullRequestReviewComment(Comment):

    def review(self) -> review.Review:
        return review.Review(self._raw["pullRequestReview"])

    def is_reply(self) -> bool:
        return self._raw["replyTo"] is not None
