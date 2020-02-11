from github import Github
from src.config import GITHUB_API_KEY

gh_client = Github(GITHUB_API_KEY)


def edit_pr_description(owner: str, repository: str, number: int, description: str):
    repo = gh_client.get_repo(f"{owner}/{repository}")
    pr = repo.get_pull(number)
    pr.edit(body=description)


def set_pull_request_assignee(owner: str, repository: str, number: int, assignee: str):
    repo = gh_client.get_repo(f"{owner}/{repository}")
    # Using get_issue here because get_pull returns a pull request which only
    # allows you to *add* an assignee, not set the assignee.
    pr = repo.get_issue(number)
    pr.edit(assignee=assignee)
