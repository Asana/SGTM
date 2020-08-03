from typing import List, Union, Tuple, Optional, Dict, Any
from datetime import datetime
from .helpers import transform_datetime, create_uuid
from src.github.models import Comment, Review, ReviewState, User
from .builder_base_class import BuilderBaseClass
from .comment_builder import CommentBuilder
from .user_builder import UserBuilder


class ReviewBuilder(BuilderBaseClass):
    def __init__(self, body: str = ""):
        self.raw_review: Dict[str, Any] = {
            "id": create_uuid(),
            "body": body,
            "author": {"login": "somebody", "name": ""},
            "comments": {"nodes": []},
            "url": "",
        }

    def state(self, state: ReviewState):
        # TODO: validate state
        self.raw_review["state"] = state.value
        return self

    def body(self, body: str):
        self.raw_review["body"] = body
        return self

    def author(self, user: Union[User, UserBuilder]):
        self.raw_review["author"] = user.to_raw()
        return self

    def submitted_at(self, submitted_at: Union[str, datetime]):
        self.raw_review["submittedAt"] = transform_datetime(submitted_at)
        return self

    def comment(self, comment: Union[CommentBuilder, Comment]):
        return self.comments([comment])

    def comments(self, comments: List[Union[CommentBuilder, Comment]]):
        for comment in comments:
            self.raw_review["comments"]["nodes"].append(comment.to_raw())  # type: ignore
        return self

    def url(self, url: str):
        self.raw_review["url"] = url
        return self

    def build(self) -> Review:
        return Review(self.raw_review)

    def to_raw(self) -> Dict[str, Any]:
        return self.build().to_raw()
