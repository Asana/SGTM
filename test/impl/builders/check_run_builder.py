from typing import Any, Dict, List, Union
from datetime import datetime
from .helpers import create_uuid, transform_datetime
from src.github.models import CheckConclusionState, CheckRun
from .builder_base_class import BuilderBaseClass


class CheckRunBuilder(BuilderBaseClass):
    def __init__(
        self,
        conclusion: CheckConclusionState = CheckConclusionState.NONE,
        is_required: bool = False,
    ):
        self.raw_check_run = {
            "node_id": create_uuid(),
            "isRequired": is_required,
            "conclusion": conclusion,
            "databaseId": create_uuid(),
        }

    def conclusion(self, conclusion: str) -> Union["CheckRunBuilder", CheckRun]:
        self.raw_check_run["conclusion"] = conclusion
        return self

    def completed_at(
        self, completed_at: Union[str, datetime]
    ) -> Union["CheckRunBuilder", CheckRun]:
        self.raw_check_run["completedAt"] = transform_datetime(completed_at)
        return self

    def is_required(self, is_required: bool) -> Union["CheckRunBuilder", CheckRun]:
        self.raw_check_run["isRequired"] = is_required
        return self

    def build(self) -> CheckRun:
        return CheckRun(self.raw_check_run)

    def to_raw(self) -> Dict[str, Any]:
        return self.build().to_raw()
