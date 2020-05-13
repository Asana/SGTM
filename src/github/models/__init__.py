from typing import Dict, Any, Union
from .pull_request import PullRequest
from .review import Review
from .comment import Comment
from .issue_comment import IssueComment
from .pull_request_review_comment import PullRequestReviewComment
from .user import User


def comment_factory(raw: Dict[str, Any]) -> Union[IssueComment, PullRequestReviewComment]:
    if raw['__typename'] == 'IssueComment':
        return IssueComment(raw)
    elif raw['__typename'] == 'PullRequestReviewComment':
        return PullRequestReviewComment(raw)
    else:
        raise Exception(f"Unexpected type found: {raw['__typename']}")
