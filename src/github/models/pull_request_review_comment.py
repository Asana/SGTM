from .comment import Comment


class PullRequestReviewComment(Comment):
    def raw_review(self) -> dict:
        return self._raw["pullRequestReview"]
