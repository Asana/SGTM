from typing import Dict, Any
from .pull_request import PullRequest, MergeableState, Assignee, AssigneeReason
from .review import Review, ReviewState
from .comment import Comment
from .issue_comment import IssueComment
from .pull_request_review_comment import PullRequestReviewComment
from .user import User
from .commit import Commit
from .label import Label
from .check_run import CheckRun, CheckConclusionState
from .check_suite import CheckSuite


def comment_factory(raw: Dict[str, Any]) -> Comment:
    if raw["__typename"] == "IssueComment":
        return IssueComment(raw)
    elif raw["__typename"] == "PullRequestReviewComment":
        return PullRequestReviewComment(raw)
    else:
        raise Exception(f"Unexpected type found: {raw['__typename']}")
