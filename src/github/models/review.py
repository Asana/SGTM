from datetime import datetime
from typing import List
from src.logger import logger
from src.utils import parse_date_string
from .comment import Comment


class Review(object):
    STATE_APPROVED = "APPROVED"
    STATE_CHANGES_REQUESTED = "CHANGES_REQUESTED"
    STATE_COMMENTED = "COMMENTED"
    STATE_DISMISSED = "DISMISSED"

    def __init__(self, raw_review):
        self.raw_review = raw_review

    def id(self) -> str:
        return self.raw_review["id"]

    def submitted_at(self) -> datetime:
        return parse_date_string(self.raw_review["submittedAt"])

    def state(self) -> str:
        return self.raw_review["state"]

    def is_approval_or_changes_requested(self) -> bool:
        return self.state() in (self.STATE_APPROVED, self.STATE_CHANGES_REQUESTED)

    def is_approval(self) -> bool:
        return self.state() == self.STATE_APPROVED

    def body(self) -> str:
        return self.raw_review["body"]

    def comments(self) -> List[Comment]:
        return [
            Comment(comment)
            for comment in self.raw_review.get("comments", {}).get("nodes", [])
        ]

    def author(self) -> dict:
        return self.raw_review["author"]

    def author_handle(self) -> str:
        return self.author()["login"]
