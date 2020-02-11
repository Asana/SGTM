from datetime import datetime
from typing import List
from src.logger import logger
from src.utils import parse_date_string
from .review import Review
from .comment import Comment


class PullRequest(object):
    def __init__(self, raw_pull_request):
        self.raw_pull_request = raw_pull_request
        self.__assignees = self._assignees_from_raw()
        self.__body = raw_pull_request["body"]

    def _assignees_from_raw(self) -> List[str]:
        return sorted(
            [node["login"] for node in self.raw_pull_request["assignees"]["nodes"]]
        )

    def assignees(self) -> List[str]:
        return self.__assignees

    def set_assignees(self, assignees: List[str]):
        self.__assignees = assignees

    def requested_reviewers(self) -> List[str]:
        return sorted(
            node["requestedReviewer"]["login"]
            for node in self.raw_pull_request["reviewRequests"]["nodes"]
        )

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
        return self.raw_pull_request["id"]

    def number(self) -> int:
        return self.raw_pull_request["number"]

    def title(self) -> int:
        return self.raw_pull_request["title"]

    def url(self) -> str:
        return self.raw_pull_request["url"]

    def repository_id(self) -> str:
        return self.raw_pull_request["repository"]["id"]

    def repository_name(self) -> str:
        return self.raw_pull_request["repository"]["name"]

    def owner_handle(self) -> str:
        return self.raw_pull_request["owner"]["login"]

    def repository_owner_handle(self) -> str:
        return self.raw_pull_request["repository"]["owner"]["login"]

    def author_handle(self) -> str:
        return self.raw_pull_request["author"]["login"]

    def body(self) -> str:
        return self.__body

    def set_body(self, body: str):
        self.__body = body

    def closed(self) -> bool:
        return self.raw_pull_request["closed"]

    def merged(self) -> bool:
        return self.raw_pull_request["merged"]

    def merged_at(self) -> datetime:
        return parse_date_string(self.raw_pull_request["mergedAt"])

    def reviews(self) -> List[Review]:
        return [Review(review) for review in self.raw_pull_request["reviews"]["nodes"]]

    def comments(self) -> List[Comment]:
        return [
            Comment(comment) for comment in self.raw_pull_request["comments"]["nodes"]
        ]
