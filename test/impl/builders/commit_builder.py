from typing import List, Union, Tuple, Optional, Dict, Any
from datetime import datetime
from .helpers import transform_datetime, create_uuid
from src.github.models import Commit
from .builder_base_class import BuilderBaseClass
from .user_builder import UserBuilder


class CommitBuilder(BuilderBaseClass):
    def __init__(self, status=Commit.BUILD_PENDING):
        self.raw_commit = {
            "commit": {"status": {"state": status}, "node_id": create_uuid(),}
        }

    def status(self, status: str) -> Union["CommitBuilder", Commit]:
        self.raw_commit["commit"]["status"]["state"] = status
        return self

    def build(self) -> Commit:
        return Commit(self.raw_commit)

    def to_raw(self) -> Dict[str, Any]:
        return self.build().to_raw()
