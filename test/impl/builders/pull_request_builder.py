from random import randint
from typing import Any, Dict, List, Union
from datetime import datetime
from .helpers import transform_datetime, create_uuid
from src.github.models import (
    PullRequest,
    Comment,
    Review,
    User,
    Commit,
    Label,
    MergeableState,
)
from .builder_base_class import BuilderBaseClass
from .user_builder import UserBuilder
from .comment_builder import CommentBuilder
from .commit_builder import CommitBuilder
from .review_builder import ReviewBuilder
from .label_builder import LabelBuilder


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
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {"state": Commit.BUILD_PENDING},
                            "node_id": create_uuid(),
                        }
                    }
                ]
            },
            "labels": {"nodes": []},
            "comments": {"nodes": []},
            "reviews": {"nodes": []},
            "reviewRequests": {"nodes": []},
            "closed": False,
            "merged": False,
            "isDraft": False,
            "mergeable": MergeableState.MERGEABLE,
            "author": {"login": UserBuilder.next_login(), "name": ""},
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

    def isDraft(self, isDraft: bool):
        self.raw_pr["isDraft"] = isDraft
        return self

    def mergeable(self, mergeable: MergeableState):
        self.raw_pr["mergeable"] = mergeable
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
            self.raw_pr["comments"]["nodes"].append(comment.to_raw())  # type: ignore
        return self

    def review(self, review: Union[ReviewBuilder, Review]):
        return self.reviews([review])

    def reviews(self, reviews: List[Union[ReviewBuilder, Review]]):
        for review in reviews:
            self.raw_pr["reviews"]["nodes"].append(review.to_raw())  # type: ignore
        return self

    def author(self, user: Union[User, UserBuilder]):
        self.raw_pr["author"] = user.to_raw()
        return self

    def assignee(self, assignee: Union[UserBuilder, User]):
        return self.assignees([assignee])

    def assignees(self, assignees: List[Union[User, UserBuilder]]):
        for assignee in assignees:
            self.raw_pr["assignees"]["nodes"].append(assignee.to_raw())  # type: ignore
        return self

    def requested_reviewer(self, requested_reviewer: Union[UserBuilder, User]):
        return self.requested_reviewers([requested_reviewer])

    def requested_reviewers(self, reviewers: List[Union[User, UserBuilder]]):
        for reviewer in reviewers:
            self.raw_pr["reviewRequests"]["nodes"].append(  # type: ignore
                {"requestedReviewer": reviewer.to_raw()}
            )
        return self

    def commit(self, commit: Union[CommitBuilder, Commit]):
        return self.commits([commit])

    def commits(self, commits: List[Union[CommitBuilder, Commit]]):
        for commit in commits:
            self.raw_pr["commits"]["nodes"].insert(0, commit.to_raw())
        return self

    def label(self, label: Union[LabelBuilder, Label]):
        return self.labels([label])

    def labels(self, labels: List[Union[LabelBuilder, Label]]):
        for label in labels:
            self.raw_pr["labels"]["nodes"].append(label.to_raw())  # type: ignore
        return self

    def requested_reviewer_team(self, team_name: str, member_logins: List[str]):
        self.raw_pr["reviewRequests"]["nodes"].append(  # type: ignore
            {
                "requestedReviewer": {
                    "name": team_name,
                    "members": {"nodes": [{"login": login} for login in member_logins]},
                }
            }
        )
        return self

    def build(self) -> PullRequest:
        return PullRequest(self.raw_pr)

    def to_raw(self) -> Dict[str, Any]:
        return self.build().to_raw()
