from datetime import datetime
from typing import List, Optional, Dict, Any
from src.logger import logger
from src.utils import parse_date_string

# from .review import Review
from .issue_comment import IssueComment
from .review import Review
from .user import User
import copy


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

    def requested_reviewers(self) -> List[str]:
        reviewer_logins = set()
        for node in self._raw["reviewRequests"]["nodes"]:
            if (
                node["requestedReviewer"] is not None
                and "login" in node["requestedReviewer"]
            ):
                reviewer_logins.add(node["requestedReviewer"]["login"])
            elif (
                node["requestedReviewer"] is not None
                and "members" in node["requestedReviewer"]
            ):
                for reviewer in node["requestedReviewer"]["members"]["nodes"]:
                    reviewer_logins.add(reviewer["login"])
        return sorted(reviewer_logins)

    def reviewers(self) -> List[str]:
        return [review.author_handle() for review in self.reviews()]

    def assignee(self) -> str:
        maybe_multi_assignees = self.assignees()
        if len(maybe_multi_assignees) == 1:
            return maybe_multi_assignees[0]
        elif len(maybe_multi_assignees) == 0:
            logger.info("GitHub PR has no assignees. Choosing author as assignee")
            return self.author_handle()
        else:
            assignee = maybe_multi_assignees[0]
            logger.info(
                "GitHub PR has multiple assignees: {} Choosing first one in alphabetical order as as assignee: {}".format(
                    maybe_multi_assignees, assignee
                )
            )
            return assignee

    def id(self) -> str:
        return self._raw["id"]

    def number(self) -> int:
        return self._raw["number"]

    def title(self) -> int:
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

    def author(self) -> User:
        return User(self._raw["author"])

    def author_handle(self) -> str:
        return self.author().login()

    def body(self) -> str:
        return self._raw["body"]

    def set_body(self, body: str):
        self._raw = copy.deepcopy(self._raw)
        self._raw["body"] = copy.deepcopy(body)

    def closed(self) -> bool:
        return self._raw["closed"]

    def merged(self) -> bool:
        return self._raw["merged"]

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
        commit = self._raw["commits"]["nodes"][0]["commit"]
        return commit["status"]["state"] if commit["status"] else None
