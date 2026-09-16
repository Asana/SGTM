"""Per-pull-request codeowner state persisted in the sgtm-objects table.

One JSON document per PR, keyed ``<pr node id>#codeowners``. It remembers what
SGTM has already done (subtasks created, who was assigned and when, comments
posted, whether the label was ever seen) so that every webhook can be handled
idempotently from a fresh GraphQL snapshot of the PR.
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

import src.aws.dynamodb_client as dynamodb_client

STATE_KEY_SUFFIX = "#codeowners"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


@dataclass
class SubtaskState:
    task_id: str
    owner_key: str
    # GitHub login of the current assignee, None when escalated to the author.
    assignee: Optional[str] = None
    assigned_at: Optional[str] = None
    assignment_reason: str = ""
    # RequirementStatus value last written to the task, for change detection.
    status: Optional[str] = None
    completed: bool = False
    # Files listed in the task the last time it was rendered, so "no longer
    # required" comments can say which files dropped out of the diff.
    files: List[str] = field(default_factory=list)
    # True once a person chose the assignee (author's review request or a
    # reassignment by hand in Asana): SGTM then never re-picks for idleness.
    manual: bool = False
    # Hashes of the last written description and custom fields, so unchanged
    # tasks are not rewritten on every webhook.
    notes_hash: str = ""
    fields_hash: str = ""
    # When SGTM created the subtask; orders subtasks when the PR is routed.
    created_at: Optional[str] = None


@dataclass
class CodeownerState:
    # When the author first added the label. None until then.
    tasks_requested_at: Optional[str] = None
    # GitHub issue-comment database ids of SGTM's own comments on the PR.
    heads_up_comment_id: Optional[int] = None
    # Hash of the heads-up comment body last written, so it is only edited
    # when the codeowned files change.
    heads_up_body_hash: str = ""
    # The comment announcing the created subtasks: the heads-up comment's id
    # when that comment was edited in place, otherwise a new comment's id.
    created_comment_id: Optional[int] = None
    # Reviewers the author chose (human review requests, author-set assignee),
    # accumulated over time because GitHub drops reviewers from reviewRequests
    # once they review.
    human_chosen_logins: List[str] = field(default_factory=list)
    # Logins SGTM itself requested as reviewers, so its own review requests
    # are not mistaken for the author's.
    sgtm_requested_logins: List[str] = field(default_factory=list)
    # The login SGTM last set as the PR's GitHub assignee (the author
    # included). While the PR is still assigned to them, SGTM may move it;
    # anyone else was put there by a person and keeps it.
    sgtm_assigned_login: Optional[str] = None
    # Whether the one "all codeowner approvals are in place" comment was posted.
    all_approved_commented: bool = False
    subtasks: Dict[str, SubtaskState] = field(default_factory=dict)

    @property
    def tasks_requested(self) -> bool:
        return self.tasks_requested_at is not None

    def remember_human_chosen(self, logins: List[str]) -> None:
        for login in logins:
            if login not in self.human_chosen_logins:
                self.human_chosen_logins.append(login)

    def remember_sgtm_requested(self, login: str) -> None:
        if login not in self.sgtm_requested_logins:
            self.sgtm_requested_logins.append(login)

    def remember_sgtm_assigned(self, login: str) -> None:
        self.sgtm_assigned_login = login

    def to_document(self) -> dict:
        document = asdict(self)
        document["subtasks"] = {
            key: asdict(subtask) for key, subtask in self.subtasks.items()
        }
        return document

    @classmethod
    def from_document(cls, document: dict) -> "CodeownerState":
        subtask_fields = set(SubtaskState.__dataclass_fields__)
        subtasks = {
            key: SubtaskState(**{k: v for k, v in value.items() if k in subtask_fields})
            for key, value in (document.get("subtasks") or {}).items()
        }
        known_fields = {f for f in cls.__dataclass_fields__ if f != "subtasks"}
        kwargs = {k: v for k, v in document.items() if k in known_fields}
        return cls(subtasks=subtasks, **kwargs)

    @staticmethod
    def key_for(pull_request_id: str) -> str:
        return pull_request_id + STATE_KEY_SUFFIX

    @classmethod
    def load(cls, pull_request_id: str) -> "CodeownerState":
        document = dynamodb_client.get_json_document(cls.key_for(pull_request_id))
        if document is None:
            return cls()
        return cls.from_document(document)

    def save(self, pull_request_id: str) -> None:
        dynamodb_client.put_json_document(
            self.key_for(pull_request_id), self.to_document()
        )
