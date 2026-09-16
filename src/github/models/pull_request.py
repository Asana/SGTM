from datetime import datetime
from typing import List, Optional, Dict, Any, Set
from src.logger import logger
from src.utils import parse_date_string
from enum import Enum, unique

# from .review import Review
from .comment import IssueComment
from .review import Review
from .commit import Commit
from .user import User
from .label import Label
import copy
import collections


class AssigneeReason(Enum):
    NO_ASSIGNEE = "NO_ASSIGNEE"
    MULTIPLE_ASSIGNEES = "MULTIPLE_ASSIGNEES"
    SINGLE_ASSIGNEE = "SIGNLE_ASSIGNEE"


Assignee = collections.namedtuple("Assignee", "login reason")


class ReviewRequest(object):
    """One entry of a pull request's `reviewRequests` connection.

    Either a user (`login`) or a team (`team_slug`, as `org/slug`) was asked
    to review. `as_code_owner` is True when GitHub itself made the request
    because of a CODEOWNERS rule rather than a person doing so.
    """

    def __init__(self, raw_review_request: Dict[str, Any]):
        self._raw = copy.deepcopy(raw_review_request)

    def as_code_owner(self) -> bool:
        return bool(self._raw.get("asCodeOwner", False))

    def _reviewer(self) -> Dict[str, Any]:
        return self._raw.get("requestedReviewer") or {}

    def is_user(self) -> bool:
        return "login" in self._reviewer()

    def is_team(self) -> bool:
        return "members" in self._reviewer() or "slug" in self._reviewer()

    def login(self) -> Optional[str]:
        return self._reviewer().get("login")

    def team_slug(self) -> Optional[str]:
        """`org/slug` for a team request, matching CODEOWNERS `@org/slug` owners."""
        if not self.is_team():
            return None
        reviewer = self._reviewer()
        return (
            reviewer.get("combinedSlug") or reviewer.get("slug") or reviewer.get("name")
        )

    def team_member_logins(self) -> List[str]:
        if not self.is_team():
            return []
        return [
            node["login"]
            for node in (self._reviewer().get("members") or {}).get("nodes", [])
        ]


@unique
class MergeableState(Enum):
    """https://developer.github.com/v4/enum/mergeablestate/"""

    CONFLICTING = "CONFLICTING"
    MERGEABLE = "MERGEABLE"
    UNKNOWN = "UNKNOWN"


class PullRequest(object):
    def __init__(self, raw_pull_request: Dict[str, Any]):
        self._raw = copy.deepcopy(raw_pull_request)
        self._assignees = self._assignees_from_raw()

    def _assignees_from_raw(self) -> List[str]:
        return sorted([node["login"] for node in self._raw["assignees"]["nodes"]])

    def assignees(self) -> List[str]:
        return self._assignees

    def set_assignees(self, assignees: List[str]):
        self._raw = copy.deepcopy(self._raw)
        self._raw["assignees"]["nodes"] = [
            {"login": assignee_login} for assignee_login in assignees
        ]
        self._assignees = self._assignees_from_raw()

    def review_requests(self) -> List[ReviewRequest]:
        return [
            ReviewRequest(node)
            for node in self._raw["reviewRequests"]["nodes"]
            if node.get("requestedReviewer") is not None
        ]

    def requested_reviewers(
        self,
        include_team_members: bool = True,
        include_codeowner_requests: bool = True,
    ) -> List[str]:
        """Logins of requested reviewers, expanding requested teams to members.

        `include_codeowner_requests=False` drops requests GitHub made on its own
        because of CODEOWNERS, keeping only the ones a person made.
        """
        reviewer_logins = set()
        for request in self.review_requests():
            if request.as_code_owner() and not include_codeowner_requests:
                continue
            login = request.login()
            if login is not None:
                reviewer_logins.add(login)
            elif request.is_team() and include_team_members:
                reviewer_logins.update(request.team_member_logins())
        return sorted(reviewer_logins)

    def human_requested_reviewer_logins(self) -> List[str]:
        """Users a person (not GitHub's codeowner auto-request) asked to review."""
        return sorted(
            login
            for request in self.review_requests()
            if not request.as_code_owner()
            for login in [request.login()]
            if login is not None
        )

    def codeowner_requested_team_slugs(self) -> List[str]:
        """Teams GitHub auto-requested because of CODEOWNERS, as `org/slug`."""
        return sorted(
            slug
            for request in self.review_requests()
            if request.as_code_owner()
            for slug in [request.team_slug()]
            if slug is not None
        )

    def reviewers(self) -> List[str]:
        return [review.author_handle() for review in self.reviews()]

    def assignee(self) -> Assignee:
        maybe_multi_assignees = self.assignees()
        if len(maybe_multi_assignees) == 1:
            return Assignee(
                login=maybe_multi_assignees[0], reason=AssigneeReason.SINGLE_ASSIGNEE
            )
        elif len(maybe_multi_assignees) == 0:
            logger.info("GitHub PR has no assignees. Choosing author as assignee")
            return Assignee(
                login=self.author_handle(), reason=AssigneeReason.NO_ASSIGNEE
            )
        else:
            assignee = maybe_multi_assignees[0]
            logger.info(
                "GitHub PR has multiple assignees: {} Choosing first one in"
                " alphabetical order as as assignee: {}".format(
                    maybe_multi_assignees, assignee
                )
            )
            return Assignee(login=assignee, reason=AssigneeReason.MULTIPLE_ASSIGNEES)

    def id(self) -> str:
        return self._raw["id"]

    def number(self) -> int:
        return self._raw["number"]

    def title(self) -> str:
        return self._raw["title"]

    def url(self) -> str:
        return self._raw["url"]

    def repository_id(self) -> str:
        return self._raw["repository"]["id"]

    def repository_name(self) -> str:
        return self._raw["repository"]["name"]

    def owner_handle(self) -> str:
        return self.owner().login()

    def owner(self) -> User:
        return User(self._raw["owner"])

    def repository_owner_handle(self) -> str:
        return self._raw["repository"]["owner"]["login"]

    def repository_full_name(self) -> str:
        return f"{self.repository_owner_handle()}/{self.repository_name()}"

    def author(self) -> User:
        return User(self._raw["author"])

    def author_handle(self) -> str:
        return self.author().login()

    def body(self) -> str:
        return self._raw["body"]

    def body_html(self) -> str:
        return self._raw["bodyHTML"]

    def set_body(self, body: str):
        self._raw = copy.deepcopy(self._raw)
        self._raw["body"] = copy.deepcopy(body)

    def set_title(self, title: str):
        self._raw = copy.deepcopy(self._raw)
        self._raw["title"] = copy.deepcopy(title)

    def closed(self) -> bool:
        return self._raw["closed"]

    def merged(self) -> bool:
        return self._raw["merged"]

    def mergeable(self) -> MergeableState:
        return MergeableState(self._raw["mergeable"])

    def is_mergeable(self) -> bool:
        return self.mergeable() == MergeableState.MERGEABLE

    def is_draft(self) -> bool:
        return self._raw["isDraft"]

    # If there are no reviews attached to the PR with an approval status
    # or changes requested status, the PR is considered to be in a needs review state.
    def is_needs_review(self) -> bool:
        if self.is_draft():
            return False
        approval_or_changes_requested_reviews = list(
            filter(lambda x: x.is_approval_or_changes_requested(), self.reviews())
        )

        if len(approval_or_changes_requested_reviews) == 0:
            return True
        return False

    # A PR is considered to be approved if the latest review attached to the PR
    # is approved. If the latest review status is changes requested, the PR is not
    # considered to be approved.
    def is_approved(self) -> bool:
        if self.is_draft():
            return False
        approval_or_changes_requested_reviews = sorted(
            (
                review
                for review in self.reviews()
                if review.is_approval_or_changes_requested()
            ),
            key=lambda r: r.submitted_at(),
        )

        if len(approval_or_changes_requested_reviews) == 0:
            return False

        latest_review = approval_or_changes_requested_reviews[-1]
        if latest_review.is_approval():
            return True
        else:
            return False

    def is_build_successful(self) -> bool:
        return self.build_status() == Commit.BUILD_SUCCESSFUL

    def is_in_merge_queue(self) -> bool:
        return self._raw["isInMergeQueue"]

    def merged_at(self) -> Optional[datetime]:
        merged_at = self._raw.get("mergedAt", None)
        if merged_at is None:
            return None
        return parse_date_string(merged_at)

    def reviews(self) -> List[Review]:
        return [Review(review) for review in self._raw["reviews"]["nodes"]]

    def comments(self) -> List[IssueComment]:
        return [IssueComment(comment) for comment in self._raw["comments"]["nodes"]]

    def to_raw(self) -> Dict[str, Any]:
        return copy.deepcopy(self._raw)

    def build_status(self) -> Optional[str]:
        return self.commits()[0].status()

    def commits(self) -> List[Commit]:
        return [Commit(commit) for commit in self._raw["commits"]["nodes"]]

    def labels(self) -> List[Label]:
        return [Label(label) for label in self._raw["labels"]["nodes"]]

    def base_ref_associated_pull_requests(self) -> int:
        return self._raw["baseRef"]["associatedPullRequests"]["totalCount"]

    def head_ref_name(self) -> str:
        """Returns the name of the head branch (source branch) of the pull request."""
        return self._raw.get("headRefName") or ""

    def head_ref_oid(self) -> Optional[str]:
        """The sha of the head commit, or None when the query did not include it."""
        return self._raw.get("headRefOid")

    def base_ref_name(self) -> str:
        """The branch this pull request merges into."""
        return str(self._raw.get("baseRefName") or "")

    def stack_base_ref_name(self) -> Optional[str]:
        """The trunk branch of the GitHub-native stack this PR belongs to, if any.

        Native stacks are evaluated (rulesets, codeowners) against the stack's
        base rather than the PR's immediate base. None for PRs outside a
        native stack, including Graphite or hand-managed stacks, which GitHub
        cannot tell apart from ordinary branches.
        """
        stack = self._raw.get("stack")
        if not stack:
            return None
        return stack.get("baseRefName")

    def is_in_native_stack(self) -> bool:
        return self.stack_base_ref_name() is not None

    def latest_commit(self) -> Optional[Commit]:
        commits = self.commits()
        return commits[0] if commits else None

    def changed_files(self) -> List[str]:
        """Paths of the files this pull request changes.

        The GraphQL fragment carries the first 100. Call
        `graphql_client.load_all_changed_files` first when
        `has_unloaded_changed_files()` is True.
        """
        files = self._raw.get("files") or {}
        return [node["path"] for node in files.get("nodes", [])]

    def changed_files_missing(self) -> bool:
        """GitHub returns a null `files` connection for very large diffs; the
        files must then be paged separately."""
        return self._raw.get("files") is None

    def has_unloaded_changed_files(self) -> bool:
        if self.changed_files_missing():
            return True
        files = self._raw.get("files") or {}
        return bool((files.get("pageInfo") or {}).get("hasNextPage", False))

    def changed_files_end_cursor(self) -> Optional[str]:
        files = self._raw.get("files") or {}
        return (files.get("pageInfo") or {}).get("endCursor")

    def set_changed_files(self, paths: List[str]):
        self._raw = copy.deepcopy(self._raw)
        self._raw["files"] = {
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [{"path": path} for path in paths],
        }
