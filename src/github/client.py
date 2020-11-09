from github import Github, PullRequest  # type: ignore
from src.config import GITHUB_API_KEY

gh_client = Github(GITHUB_API_KEY)


def _get_pull_request(owner: str, repository: str, number: int) -> PullRequest:
    repo = gh_client.get_repo(f"{owner}/{repository}")
    pr = repo.get_pull(number)
    return pr


def edit_pr_description(owner: str, repository: str, number: int, description: str):
    pr = _get_pull_request(owner, repository, number)
    pr.edit(body=description)


def edit_pr_title(owner: str, repository: str, number: int, title: str):
    pr = _get_pull_request(owner, repository, number)
    pr.edit(title=title)


def add_pr_comment(owner: str, repository: str, number: int, comment: str):
    pr = _get_pull_request(owner, repository, number)
    pr.create_issue_comment(comment)


def set_pull_request_assignee(owner: str, repository: str, number: int, assignee: str):
    repo = gh_client.get_repo(f"{owner}/{repository}")
    # Using get_issue here because get_pull returns a pull request which only
    # allows you to *add* an assignee, not set the assignee.
    pr = repo.get_issue(number)
    pr.edit(assignee=assignee)


def merge_pull_request(owner: str, repository: str, number: int, title: str, body: str):
    pr = _get_pull_request(owner, repository, number)

    # we add the PR number to match Github's default squash and merge title style
    # which we rely on for code review tests.
    title_with_number = f"{title} (#{number})"
    pr.merge(commit_title=title_with_number, commit_message=body, merge_method="squash")
