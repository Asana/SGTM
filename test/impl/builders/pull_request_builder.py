from random import randint
from typing import Any, Dict, List, Optional, Union
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
            "bodyHTML": f"<p>{body}</p>",
            "headRefName": "feature/test-branch",
            "headRefOid": create_uuid(),
            "baseRefName": "master",
            "baseRef": {"associatedPullRequests": {"totalCount": 0}},
            "stack": None,
            "files": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [],
            },
            "title": create_uuid(),
            "url": "https://www.github.com/foo/pulls/" + str(pr_number),
            "assignees": {"nodes": []},
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {"state": Commit.BUILD_PENDING},
                            "node_id": create_uuid(),
                            "oid": create_uuid(),
                            "committedDate": "2026-01-01T00:00:00Z",
                            "checkSuites": {"nodes": []},
                        }
                    }
                ]
            },
            "labels": {"nodes": []},
            "comments": {"nodes": []},
            "reviews": {"nodes": []},
            "reviewRequests": {"nodes": []},
            "isInMergeQueue": False,
            "closed": False,
            "merged": False,
            "isDraft": False,
            "mergeable": MergeableState.MERGEABLE,
            "author": {"login": UserBuilder.next_login(), "name": ""},
            "repository": {
                "id": create_uuid(),
                "name": create_uuid(),
                "owner": {"login": create_uuid(), "name": create_uuid()},
                "defaultBranchRef": {"name": "master"},
            },
            "owner": {"login": create_uuid(), "name": create_uuid()},
        }

    def node_id(self, node_id: str):
        """Set the GraphQL node id, e.g. to build several snapshots of one PR."""
        self.raw_pr["id"] = node_id
        return self

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
        self.raw_pr["bodyHTML"] = f"<p>{body}</p>"
        return self

    def isInMergeQueue(self, is_in_merge_queue: bool):
        self.raw_pr["isInMergeQueue"] = is_in_merge_queue
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

    def requested_reviewer(
        self,
        requested_reviewer: Union[UserBuilder, User],
        as_code_owner: bool = False,
    ):
        return self.requested_reviewers([requested_reviewer], as_code_owner)

    def requested_reviewers(
        self, reviewers: List[Union[User, UserBuilder]], as_code_owner: bool = False
    ):
        for reviewer in reviewers:
            self.raw_pr["reviewRequests"]["nodes"].append(  # type: ignore
                {"asCodeOwner": as_code_owner, "requestedReviewer": reviewer.to_raw()}
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

    def requested_reviewer_team(
        self,
        team_name: str,
        member_logins: List[str],
        combined_slug: Optional[str] = None,
        as_code_owner: bool = False,
    ):
        combined_slug = combined_slug or f"org/{team_name}"
        self.raw_pr["reviewRequests"]["nodes"].append(  # type: ignore
            {
                "asCodeOwner": as_code_owner,
                "requestedReviewer": {
                    "name": team_name,
                    "slug": combined_slug.split("/", 1)[-1],
                    "combinedSlug": combined_slug,
                    "members": {"nodes": [{"login": login} for login in member_logins]},
                },
            }
        )
        return self

    def base_ref_name(self, name: str):
        self.raw_pr["baseRefName"] = name
        return self

    def files_missing(self):
        """Mimic GitHub returning a null `files` connection for a huge diff."""
        self.raw_pr["files"] = None
        return self

    def head_ref_oid(self, oid: str):
        self.raw_pr["headRefOid"] = oid
        return self

    def stack_base_ref_name(self, name: str):
        """Mark the PR as part of a GitHub-native stack targeting `name`."""
        self.raw_pr["stack"] = {"baseRefName": name}
        return self

    def files(
        self,
        paths: List[str],
        has_next_page: bool = False,
        end_cursor: Optional[str] = None,
    ):
        self.raw_pr["files"] = {
            "pageInfo": {"hasNextPage": has_next_page, "endCursor": end_cursor},
            "nodes": [{"path": path} for path in paths],
        }
        return self

    def base_ref_associated_pull_requests(self, associated_pull_requests: int):
        self.raw_pr["baseRef"]["associatedPullRequests"][
            "totalCount"
        ] = associated_pull_requests
        return self

    def head_ref_name(self, name: str):
        """Set the head branch name (source branch)."""
        self.raw_pr["headRefName"] = name
        return self

    def repository_owner(self, owner_login: str):
        """Set the repository owner login."""
        self.raw_pr["repository"]["owner"]["login"] = owner_login
        return self

    def repository_name(self, name: str):
        """Set the repository name."""
        self.raw_pr["repository"]["name"] = name
        return self

    def default_branch_name(self, name: str):
        """Set the repository's default branch."""
        self.raw_pr["repository"]["defaultBranchRef"] = {"name": name}
        return self

    def build(self) -> PullRequest:
        return PullRequest(self.raw_pr)

    def to_raw(self) -> Dict[str, Any]:
        return self.build().to_raw()
