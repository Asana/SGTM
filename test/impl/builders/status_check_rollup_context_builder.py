from typing import Any, Dict, Union
from datetime import datetime
from .helpers import create_uuid, transform_datetime
from src.github.models import CheckRun
from .builder_base_class import BuilderBaseClass


class StatusCheckRollupContextBuilder(BuilderBaseClass):
    def __init__(self, typename: str):
        self.raw_status_check_rollup_context = {
            "node_id": create_uuid(),
            "databaseId": create_uuid(),
        }

    def completed_at(
        self, completed_at: Union[str, datetime]
    ) -> Union["CheckRunBuilder", CheckRun]:
        self.raw_check_run["completedAt"] = transform_datetime(completed_at)
        return self

    def build(self) -> CheckRun:
        return CheckRun(self.raw_check_run)

    def to_raw(self) -> Dict[str, Any]:
        return self.build().to_raw()
