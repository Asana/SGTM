from datetime import datetime
from typing import List
from src.logger import logger
from src.utils import parse_date_string


class Comment(object):
    def __init__(self, raw_comment):
        self.raw_comment = raw_comment

    def id(self) -> str:
        return self.raw_comment["id"]

    def published_at(self) -> datetime:
        return parse_date_string(self.raw_comment["publishedAt"])

    def body(self) -> str:
        return self.raw_comment["body"]

    def author_handle(self) -> str:
        return self.author()["login"]

    def author(self) -> dict:
        return self.raw_comment["author"]
