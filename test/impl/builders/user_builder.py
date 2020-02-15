from typing import Dict, Any

from src.github.models import User

from .helpers import create_uuid


class UserBuilder(object):
    def __init__(self, login: str = "somebody", name: str = ""):
        self.raw_user = {
            "id": create_uuid(),
            "login": login,
            "name": name
        }

    def login(self, login: str):
        self.raw_user["login"] = login
        return self

    def name(self, name: str):
        self.raw_user["name"] = name
        return self

    def build(self) -> User:
        return User(self.raw_user)

    def to_raw(self) -> Dict[str, Any]:
        return self.build().to_raw()
