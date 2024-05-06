import requests
from requests.auth import HTTPBasicAuth

from github import Github, PullRequest  # type: ignore
from src.config import GITHUB_API_KEY  # HGTODO

gh_client = Github(GITHUB_API_KEY)


def _get_pull_request(owner: str, repository: str, number: int) -> PullRequest:  # type: ignore
    repo = gh_client.get_repo(f"{owner}/{repository}")
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


def set_pull_request_assignee(owner: str, repository: str, number: int, assignee: str):
    repo = gh_client.get_repo(f"{owner}/{repository}")
    # Using get_issue here because get_pull returns a pull request which only
    # allows you to *add* an assignee, not set the assignee.
    pr = repo.get_issue(number)
    pr.edit(assignee=assignee)  # type: ignore


def merge_pull_request(owner: str, repository: str, number: int, title: str, body: str):
    pr = _get_pull_request(owner, repository, number)

    # we add the PR number to match Github's default squash and merge title style
    # which we rely on for code review tests.
    title_with_number = f"{title} (#{number})"
    pr.merge(commit_title=title_with_number, commit_message=body, merge_method="squash")  # type: ignore


def rerequest_check_run(owner: str, repository: str, check_run_id: int):
    auth = HTTPBasicAuth(GITHUB_API_KEY, "")
    url = "https://api.github.com/repos/{owner}/{repository}/check-runs/{check_run_id}/rerequest".format(
        owner=owner, repository=repository, check_run_id=check_run_id
    )
    # Some check runs cannot be rerequested. See https://docs.github.com/en/rest/checks/runs?apiVersion=2022-11-28#rerequest-a-check-run--status-codes
    return requests.post(url, auth=auth).status_code == 201


## permissions needed: get pull request, get issues, PR edits, request check run
