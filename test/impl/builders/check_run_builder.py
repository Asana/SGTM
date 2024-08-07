from typing import Any, Dict, Union
from datetime import datetime
from .helpers import create_uuid, transform_datetime
from src.github.models import CheckRun
from .builder_base_class import BuilderBaseClass


class CheckRunBuilder(BuilderBaseClass):
    def __init__(
        self,
    ):
        self.raw_check_run = {
            "node_id": create_uuid(),
            "databaseId": create_uuid(),
        }

    def completed_at(
        self, completed_at: Union[str, datetime, None]
    ) -> Union["CheckRunBuilder", CheckRun]:
        self.raw_check_run["completedAt"] = (
            transform_datetime(completed_at) if completed_at else None
        )
        return self

    def build(self) -> CheckRun:
        return CheckRun(self.raw_check_run)

    def to_raw(self) -> Dict[str, Any]:
        return self.build().to_raw()
