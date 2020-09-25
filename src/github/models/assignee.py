from enum import Enum


class AssigneeReason(Enum):
    NO_ASSIGNEE = "NO_ASSIGNEE"
    MULTIPLE_ASSIGNEES = "MULTIPLE_ASSIGNEES"
    SINGLE_ASSIGNEE = "SIGNLE_ASSIGNEE"


class Assignee(object):
    def __init__(self, handle: str, reason: AssigneeReason):
        self.handle = handle
        self.reason = reason

    def get_handle(self) -> str:
        return self.handle

    def get_assignee_reason(self) -> AssigneeReason:
        return self.reason
