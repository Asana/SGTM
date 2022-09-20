from typing import Dict, Any
from src.github.models import User
from .helpers import create_uuid
from .builder_base_class import BuilderBaseClass


class UserBuilder(BuilderBaseClass):
    LOGIN_COUNTER = 0

    def __init__(self, login: str = None, name: str = ""):
        if login is None:
            login = "somebody_" + self.LOGIN_COUNTER
            self.LOGIN_COUNTER += 1
        self.raw_user = {"id": create_uuid(), "login": login, "name": name}

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
