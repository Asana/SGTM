from datetime import datetime
from typing import Any, Dict, List, Union
from .helpers import create_uuid, transform_datetime
from src.github.models import Commit, CheckSuite
from .builder_base_class import BuilderBaseClass
from .check_suite_builder import CheckSuiteBuilder


class CommitBuilder(BuilderBaseClass):
    def __init__(self, status=Commit.BUILD_PENDING):
        self.raw_commit = {
            "commit": {
                "statusCheckRollup": {"state": status},
                "node_id": create_uuid(),
                "oid": create_uuid(),
                "committedDate": "2026-01-01T00:00:00Z",
                "checkSuites": {"nodes": []},
            }
        }

    def status(self, status: str) -> Union["CommitBuilder", Commit]:
        self.raw_commit["commit"]["statusCheckRollup"]["state"] = status
        return self

    def oid(self, oid: str) -> Union["CommitBuilder", Commit]:
        self.raw_commit["commit"]["oid"] = oid
        return self

    def committed_date(
        self, committed_date: Union[str, datetime]
    ) -> Union["CommitBuilder", Commit]:
        self.raw_commit["commit"]["committedDate"] = transform_datetime(committed_date)
        return self

    def check_suites(
        self, check_suites: List[Union[CheckSuiteBuilder, CheckSuite]]
    ) -> Union["CommitBuilder", Commit]:
        for check_suite in check_suites:
            self.raw_commit["commit"]["checkSuites"]["nodes"].append(
                check_suite.to_raw()
            )
        return self

    def build(self) -> Commit:
        return Commit(self.raw_commit)

    def to_raw(self) -> Dict[str, Any]:
        return self.build().to_raw()
