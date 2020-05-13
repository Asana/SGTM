from random import randint
from typing import List, Union, Tuple, Optional, Dict, Any
from datetime import datetime
from .helpers import transform_datetime, create_uuid
from src.github.models import PullRequest, Comment, Review, User
from .builder_base_class import BuilderBaseClass
from .user_builder import UserBuilder
from .comment_builder import CommentBuilder
from .review_builder import ReviewBuilder


class PullRequestBuilder(BuilderBaseClass):
    def __init__(self, body: str = ""):
        pr_number = randint(1, 9999999999)
        self.raw_pr: Dict[str, Any] = {
            "id": create_uuid(),
            "number": pr_number,
            "body": body,
            "title": create_uuid(),
            "url": "https://www.github.com/foo/pulls/" + str(pr_number),
            "assignees": {"nodes": []},
            "comments": {"nodes": []},
            "reviews": {"nodes": []},
            "reviewRequests": {"nodes": []},
            "closed": False,
            "merged": False,
            "author": {"login": "somebody", "name": ""},
            "repository": {
                "id": create_uuid(),
                "name": create_uuid(),
                "owner": {"login": create_uuid(), "name": create_uuid()},
            },
        }

    def closed(self, closed: bool):
        self.raw_pr["closed"] = closed
        return self

    def merged(self, merged: bool):
        self.raw_pr["merged"] = merged
        return self

    def number(self, number: str):
        self.raw_pr["number"] = number
        return self

    def url(self, url: str):
        self.raw_pr["url"] = url
        return self

    def title(self, title: str):
        self.raw_pr["title"] = title
        return self

    def body(self, body: str):
        self.raw_pr["body"] = body
        return self

    def merged_at(self, merged_at: Union[str, datetime]):
        self.raw_pr["mergedAt"] = transform_datetime(merged_at)
        return self

    def comment(self, comment: Union[CommentBuilder, Comment]):
        return self.comments([comment])

    def comments(self, comments: List[Union[CommentBuilder, Comment]]):
        for comment in comments:
            self.raw_pr["comments"]["nodes"].append(comment.to_raw())
        return self

    def review(self, review: Union[ReviewBuilder, Review]):
        return self.reviews([review])

    def reviews(self, reviews: List[Union[ReviewBuilder, Review]]):
        for review in reviews:
            self.raw_pr["reviews"]["nodes"].append(review.to_raw())
        return self

    def author(self, user: Union[User, UserBuilder]):
        self.raw_pr["author"] = user.to_raw()
        return self

    def assignee(self, assignee: Union[UserBuilder, User]):
        return self.assignees([assignee])

    def assignees(self, assignees: List[Union[User, UserBuilder]]):
        for assignee in assignees:
            self.raw_pr["assignees"]["nodes"].append(assignee.to_raw())
        return self

    def requested_reviewer(self, requested_reviewer: Union[UserBuilder, User]):
        return self.requested_reviewers([requested_reviewer])

    def requested_reviewers(self, reviewers: List[Union[User, UserBuilder]]):
        for reviewer in reviewers:
            self.raw_pr["reviewRequests"]["nodes"].append(
                {"requestedReviewer": reviewer.to_raw()}
            )
        return self

    def build(self) -> PullRequest:
        return PullRequest(self.raw_pr)

    def to_raw(self) -> Dict[str, Any]:
        return self.build().to_raw()
