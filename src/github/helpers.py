from src.github.models import PullRequest


def pull_request_has_label(pull_request: PullRequest, label: str) -> bool:
    label_names = map(lambda label: label.name(), pull_request.labels())
    return label in label_names


def pull_request_has_comment(pull_request: PullRequest, comment: str) -> bool:
    return any(
        existing_comment.body() == comment
        for existing_comment in pull_request.comments()
    )
