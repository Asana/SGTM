from github import Github  # type: ignore
from src.config import GITHUB_API_KEY

gh_client = Github(GITHUB_API_KEY)


def _get_pull_request(owner: str, repository: str, number: int):
    repo = gh_client.get_repo(f"{owner}/{repository}")
    pr = repo.get_pull(number)
    return pr


def edit_pr_description(owner: str, repository: str, number: int, description: str):
    pr = _get_pull_request(owner, repository, number)
    pr.edit(body=description)


def set_pull_request_assignee(owner: str, repository: str, number: int, assignee: str):
    repo = gh_client.get_repo(f"{owner}/{repository}")
    # Using get_issue here because get_pull returns a pull request which only
    # allows you to *add* an assignee, not set the assignee.
    pr = repo.get_issue(number)
    pr.edit(assignee=assignee)


def merge_pull_request(owner: str, repository: str, number: int, title: str, body: str):
    pr = _get_pull_request(owner, repository, number)
    pr.merge(commit_title=title, commit_message=body, commit_merge_method="squash")
