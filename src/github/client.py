import requests
from requests.auth import HTTPBasicAuth
from typing import List, Optional

from github import GithubException, PullRequest, UnknownObjectException  # type: ignore
from src.github.get_app_token import sgtm_github_auth
from src.logger import logger


def _get_repo(owner: str, repository: str):  # type: ignore
    return sgtm_github_auth(owner).get_rest_client().get_repo(f"{owner}/{repository}")


def _get_pull_request(owner: str, repository: str, number: int) -> PullRequest:  # type: ignore
    repo = _get_repo(owner, repository)
    pr = repo.get_pull(number)
    return pr  # type: ignore


def edit_pr_description(owner: str, repository: str, number: int, description: str):
    pr = _get_pull_request(owner, repository, number)
    pr.edit(body=description)  # type: ignore


def edit_pr_title(owner: str, repository: str, number: int, title: str):
    pr = _get_pull_request(owner, repository, number)
    pr.edit(title=title)  # type: ignore


def add_pr_comment(owner: str, repository: str, number: int, comment: str):
    pr = _get_pull_request(owner, repository, number)
    pr.create_issue_comment(comment)  # type: ignore


def edit_comment(
    owner: str, repository: str, number: int, comment_id: Optional[int], new_body: str
):
    if comment_id is None:
        raise ValueError("Comment ID is required")
    pr = _get_pull_request(owner, repository, number)
    comment = pr.get_issue_comment(comment_id)  # type: ignore
    comment.edit(body=new_body)  # type: ignore


def delete_comment(owner: str, repository: str, number: int, comment_id: Optional[int]):
    if comment_id is None:
        raise ValueError("Comment ID is required")
    pr = _get_pull_request(owner, repository, number)
    comment = pr.get_issue_comment(comment_id)  # type: ignore
    comment.delete()  # type: ignore


def set_pull_request_assignee(owner: str, repository: str, number: int, assignee: str):
    repo = _get_repo(owner, repository)
    # Using get_issue here because get_pull returns a pull request which only
    # allows you to *add* an assignee, not set the assignee.
    pr = repo.get_issue(number)
    pr.edit(assignee=assignee)  # type: ignore


def request_reviewers(
    owner: str, repository: str, number: int, reviewers: List[str]
) -> List[str]:
    """Ask the given users to review the pull request, one request per user so
    that one rejected login (not a collaborator any more, the author) does not
    stop the others. Returns the logins GitHub accepted.

    Note that GitHub treats a request for someone who already reviewed as a
    re-request: they are asked again and notified. Callers decide whether that
    is wanted.
    """
    if not reviewers:
        return []
    pr = _get_pull_request(owner, repository, number)
    requested: List[str] = []
    for reviewer in reviewers:
        try:
            pr.create_review_request(reviewers=[reviewer])  # type: ignore
            requested.append(reviewer)
        except GithubException as e:
            logger.warning(
                f"Could not request a review from {reviewer} on "
                f"{owner}/{repository}#{number}: {e}"
            )
    return requested


# GitHub rejects label descriptions longer than this.
LABEL_DESCRIPTION_MAX_LENGTH = 100


def ensure_label(owner: str, repository: str, name: str, color: str, description: str):
    """Create the label in the repository if it does not exist yet.

    `color` is a hex string without the leading `#`. Creating labels needs the
    Issues: write permission (labels are an issues resource).
    """
    repo = _get_repo(owner, repository)
    try:
        repo.get_label(name)
        return
    except UnknownObjectException:
        pass
    logger.info(f"Creating label '{name}' in {owner}/{repository}")
    try:
        repo.create_label(
            name=name,
            color=color,
            description=description[:LABEL_DESCRIPTION_MAX_LENGTH],
        )
    except GithubException as e:
        # Another invocation created it in between: the end state is what we want.
        if e.status == 422:
            logger.info(f"Label '{name}' already exists in {owner}/{repository}")
            return
        raise


def merge_pull_request(owner: str, repository: str, number: int, title: str, body: str):
    pr = _get_pull_request(owner, repository, number)

    # we add the PR number to match Github's default squash and merge title style
    # which we rely on for code review tests.
    title_with_number = f"{title} (#{number})"
    try:
        pr.enable_automerge(commit_headline=title_with_number, commit_body=body)  # type: ignore
    except Exception as e:
        logger.info(
            f"Failed to enable automerge for PR {title_with_number}, with error {e}"
        )
        logger.info("Merging PR manually")
        pr.merge(commit_title=title_with_number, commit_message=body, merge_method="squash")  # type: ignore


def rerequest_check_run(owner: str, repository: str, check_run_id: int):
    auth = HTTPBasicAuth(sgtm_github_auth(owner).get_token().token, "")
    url = "https://api.github.com/repos/{owner}/{repository}/check-runs/{check_run_id}/rerequest".format(
        owner=owner, repository=repository, check_run_id=check_run_id
    )
    # Some check runs cannot be rerequested. See https://docs.github.com/en/rest/checks/runs?apiVersion=2022-11-28#rerequest-a-check-run--status-codes
    return requests.post(url, auth=auth).status_code == 201
