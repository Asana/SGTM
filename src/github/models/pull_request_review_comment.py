from .comment import Comment
from .review import Review

class PullRequestReviewComment(Comment):

    def review(self) -> Review:
        # XCXC: Make a separate type for IssueComment and PullRequestReviewComment
        # only the latter would implement this.
        return Review(self._raw['pullRequestReview'])
