from typing import Any, Dict, List, Union
from .helpers import create_uuid
from src.github.models import Commit, StatusCheckRollupContext
from .builder_base_class import BuilderBaseClass
from .status_check_rollup_context_builder import StatusCheckRollupContextBuilder


class CommitBuilder(BuilderBaseClass):
    def __init__(self):
        self.raw_commit = {
            "commit": {
                "statusCheckRollup": {"contexts": {"nodes": []}},
                "node_id": create_uuid(),
            }
        }

    def status(self, status: str) -> Union["CommitBuilder", Commit]:
        self.raw_commit["commit"]["statusCheckRollup"]["state"] = status
        return self

    def status_check_rollup_contexts(
        self,
        status_check_rollup_contexts: List[
            Union[StatusCheckRollupContextBuilder, StatusCheckRollupContext]
        ],
    ) -> Union["CommitBuilder", Commit]:
        for status_check_rollup_context in status_check_rollup_contexts:
            self.raw_commit["commit"]["statusCheckRollup"]["contexts"]["nodes"].append(
                status_check_rollup_context.to_raw()
            )
        return self

    def build(self) -> Commit:
        return Commit(self.raw_commit)

    def to_raw(self) -> Dict[str, Any]:
        return self.build().to_raw()
