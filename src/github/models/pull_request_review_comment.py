"""
    #CyclicDependencyBetweenCommentAndReview

    Because we want to support both comment.review(), which returns a Review object,
    and review.comments(), which returns a list of PullRequestReviewComment objects,
    we have a cyclic dependency between review.py, and pull_request_review_comment.py.

    One way to get around this is to import the module itself, not the class.
    So, in pull_request_review_comment.py, we import the module `review`.
    And in review.py, we import the module `pull_request_review_comment`.

    This solves the issue for the implementations of review() and comments(),
    but if we want to use type annotations for the return types, we still have a problem.
    For that reason, we need `from __future__import annotations`,
    which postpones evaluation of type hints [1].

    [1] https://www.python.org/dev/peps/pep-0563
"""
from __future__ import annotations
from .comment import Comment
from . import review


class PullRequestReviewComment(Comment):
    def review(self) -> review.Review:
        return review.Review(self._raw["pullRequestReview"])
