"""What the PR task's fields and description need to know about codeowners."""
from dataclasses import dataclass
from typing import Dict, Optional

from .state import CodeownerState
from .status import CodeownerSummary


@dataclass
class CodeownerTaskContext:
    summary: CodeownerSummary
    state: CodeownerState
    label: str

    def assignees_by_owner_key(self) -> Dict[str, Optional[str]]:
        return {key: sub.assignee for key, sub in self.state.subtasks.items()}

    def subtask_ids_by_owner_key(self) -> Dict[str, str]:
        return {key: sub.task_id for key, sub in self.state.subtasks.items()}

    def manages_pull_request_assignee(self) -> bool:
        """True once codeowner tasks were requested for a PR with codeowned
        files: the codeowner rules then decide who the PR is assigned to after
        a review, instead of SGTM's plain "back to the author" rule."""
        return self.summary.has_codeowned_files() and self.state.tasks_requested
