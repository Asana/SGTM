from .comment import Comment
from .review import Review


class PullRequestReviewComment(Comment):
    def review(self) -> Review:
        return Review(self._raw["pullRequestReview"])
