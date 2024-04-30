from typing import Union, Dict, Any
from datetime import datetime
from .helpers import transform_datetime, create_uuid
from src.github.models import Comment, User
from .builder_base_class import BuilderBaseClass
from .user_builder import UserBuilder


class CommentBuilder(BuilderBaseClass):
    def __init__(self, body: str = "", url: str = ""):
        self.raw_comment = {
            "id": create_uuid(),
            "body": body,
            "author": {"login": UserBuilder.next_login(), "name": ""},
            "url": url,
        }

    def body(self, body: str):
        self.raw_comment["body"] = body
        return self

    def author(self, user: Union[User, UserBuilder]):
        self.raw_comment["author"] = user.to_raw()
        return self

    def published_at(self, published_at: Union[str, datetime]):
        self.raw_comment["publishedAt"] = transform_datetime(published_at)
        return self

    def build(self) -> Comment:
        return Comment(self.raw_comment)

    def to_raw(self) -> Dict[str, Any]:
        return self.build().to_raw()

    def url(self, url: str):
        self.raw_comment["url"] = url
        return self
