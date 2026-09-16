from typing import Tuple, FrozenSet, Optional, List
from sgqlc.endpoint.http import HTTPEndpoint  # type: ignore
from src.github.get_app_token import sgtm_github_auth
from src.logger import logger
from src.github.models import comment_factory, PullRequest, Review, Comment
from .queries import (
    GetPullRequest,
    GetPullRequestByRepositoryAndNumber,
    GetPullRequestAndComment,
    GetPullRequestAndReview,
    GetPullRequestFiles,
    GetRepositoryFileContent,
    IteratePullRequestIdsForCommitId,
    IterateReviewsForPullRequestId,
    GetTeamMembers,
)

####################################################################################################
####### Core GraphQL Client helpers
####################################################################################################


def _execute_graphql_query(
    org_name: str, query: FrozenSet[str], variables: dict
) -> dict:
    query_str = "\n".join(query)

    response = sgtm_github_auth(org_name).get_graphql_endpoint()(query_str, variables)
    if "errors" in response:
        raise ValueError(f"Error in graphql query:\n{response }")
    data = response["data"]
    # if len(data.keys()) == 1:
    #     return data[list(data.keys())[0]]
    return data


####################################################################################################
####### Specific queries
####################################################################################################


def get_pull_request(org_name: str, pull_request_id: str) -> PullRequest:
    data = _execute_graphql_query(
        org_name, GetPullRequest, {"pullRequestId": pull_request_id}
    )
    return PullRequest(data["pullRequest"])


def get_pull_request_by_repository_and_number(
    org_name: str, repository_node_id: str, pull_request_number: int
) -> PullRequest:
    data = _execute_graphql_query(
        org_name,
        GetPullRequestByRepositoryAndNumber,
        {"repositoryId": repository_node_id, "pullRequestNumber": pull_request_number},
    )
    return PullRequest(data["repository"]["pullRequest"])


def get_pull_request_and_comment(
    org_name: str, pull_request_id: str, comment_id: str
) -> Tuple[PullRequest, Comment]:
    data = _execute_graphql_query(
        org_name,
        GetPullRequestAndComment,
        {"pullRequestId": pull_request_id, "commentId": comment_id},
    )
    return PullRequest(data["pullRequest"]), comment_factory(data["comment"])


def get_pull_request_and_review(
    org_name: str, pull_request_id: str, review_id: str
) -> Tuple[PullRequest, Review]:
    data = _execute_graphql_query(
        org_name,
        GetPullRequestAndReview,
        {"pullRequestId": pull_request_id, "reviewId": review_id},
    )
    return PullRequest(data["pullRequest"]), Review(data["review"])


def get_pull_request_for_commit_id(
    org_name: str, commit_id: str
) -> Optional[PullRequest]:
    """Get the PullRequest given a commit id.

    Every commit is associated with one or more pull requests.
    We're only interested in the first pull request where the head commit (latest commit) matches the given commit id.
    We could match commit shas but commit ids are more stable.

    TODO: handle multiple pull requests for a commit id.
    """

    def is_last_commit(pull_request_edge):
        last_commit_id = pull_request_edge["node"]["commits"]["nodes"][0]["commit"][
            "id"
        ]
        return last_commit_id == commit_id

    pull_request_edges = _execute_graphql_query(
        org_name, IteratePullRequestIdsForCommitId, {"commitId": commit_id}
    )["commit"]["associatedPullRequests"]["edges"]
    while pull_request_edges:
        try:
            match = next(
                (e["node"]["id"] for e in pull_request_edges if is_last_commit(e))
            )
            return get_pull_request(org_name, match)
        except StopIteration:
            pull_request_edges = _execute_graphql_query(
                org_name,
                IteratePullRequestIdsForCommitId,
                {
                    "commitId": commit_id,
                    "cursor": pull_request_edges[-1]["cursor"],
                },
            )["commit"]["associatedPullRequests"]["edges"]
    return None


def get_review_for_database_id(
    org_name: str, pull_request_id: str, review_db_id: str
) -> Optional[Review]:
    """Get the PullRequestReview given a pull request and the NUMERIC id id of the review.

    NOTE: `pull_request_id` and `review_db_id are DIFFERENT types of ids.

    The github API has two ids for each object:
        `id`: a base64-encoded string (also known as "node_id").
        `databaseId`: the primary key from the database.

    In this function:
        @pull_request_id is the `id` for the pull request.
        @review_db_id is the `databaseId` for the review.

    Unfortunately, this requires iterating through all reviews on the given pull request.

    See https://developer.github.com/v4/object/repository/#fields
    """

    def is_review(review_edge):
        return review_edge["node"]["databaseId"] == review_db_id

    review_edges = _execute_graphql_query(
        org_name, IterateReviewsForPullRequestId, {"pullRequestId": pull_request_id}
    )["node"]["reviews"]["edges"]
    while review_edges:
        try:
            match = next((e["node"] for e in review_edges if is_review(e)))
            return Review(match)
        except StopIteration:
            # no matching reviews, continue.
            review_edges = _execute_graphql_query(
                org_name,
                IterateReviewsForPullRequestId,
                {
                    "pullRequestId": pull_request_id,
                    "cursor": review_edges[-1]["cursor"],
                },
            )["node"]["reviews"]["edges"]
    return None


def get_pull_request_files(
    org_name: str, pull_request_id: str, cursor: Optional[str] = None
) -> Tuple[List[str], Optional[str]]:
    """Fetch one page of a pull request's changed file paths.

    Returns the paths on that page and the cursor for the next page, or None
    when this was the last page.
    """
    variables: dict = {"pullRequestId": pull_request_id}
    if cursor is not None:
        variables["cursor"] = cursor
    files = _execute_graphql_query(org_name, GetPullRequestFiles, variables)[
        "pullRequest"
    ]["files"]
    paths = [node["path"] for node in files["nodes"]]
    page_info = files["pageInfo"]
    next_cursor = page_info["endCursor"] if page_info["hasNextPage"] else None
    return paths, next_cursor


def load_all_changed_files(org_name: str, pull_request: PullRequest) -> None:
    """Make sure `pull_request.changed_files()` holds every changed file.

    The FullPullRequest fragment carries the first 100 files; this pages
    through the rest for larger pull requests and stores the complete list on
    the object.
    """
    if not pull_request.has_unloaded_changed_files():
        return
    paths = list(pull_request.changed_files())
    cursor = pull_request.changed_files_end_cursor()
    # GitHub returns a null `files` connection for very large diffs; page from
    # the start in that case.
    fetch_first_page = pull_request.changed_files_missing()
    while fetch_first_page or cursor is not None:
        page, cursor = get_pull_request_files(org_name, pull_request.id(), cursor)
        paths.extend(page)
        fetch_first_page = False
    pull_request.set_changed_files(paths)


def get_repository_file_content(
    org_name: str, owner: str, repository: str, ref: str, path: str
) -> Optional[str]:
    """Return the text of a file at branch `ref`, or None if the file does not
    exist there. Raises ValueError when the branch itself does not exist, so a
    deleted base branch is not mistaken for a repository without the file.

    Used to read CODEOWNERS from a pull request's base branch. Requires the
    GitHub App to have read access to repository contents.
    """
    data = _execute_graphql_query(
        org_name,
        GetRepositoryFileContent,
        {
            "owner": owner,
            "name": repository,
            "ref": f"refs/heads/{ref}",
            "expression": f"{ref}:{path}",
        },
    )
    repository_data = data.get("repository") or {}
    if repository_data.get("ref") is None:
        raise ValueError(f"Branch {ref} does not exist in {owner}/{repository}")
    blob = repository_data.get("object")
    if not blob or blob.get("__typename") != "Blob" or blob.get("text") is None:
        return None
    if blob.get("isTruncated"):
        raise ValueError(f"{path} at {ref} is too large to read via GraphQL")
    return blob["text"]


def get_team_members(org: str, team_slug: str) -> List[str]:
    """All members of a GitHub team, paging through teams larger than 100.

    Returns an empty list, and logs an error, when the team does not exist or
    is not visible to SGTM (the GitHub App needs Members: Read on the
    organization).
    """
    logins: List[str] = []
    variables: dict = {"org": org, "teamSlug": team_slug}
    while True:
        data = _execute_graphql_query(org, GetTeamMembers.GetTeamMembers, variables)
        team = data["organization"]["team"]
        if not team:
            logger.error(
                f"GitHub team {org}/{team_slug} was not found or is not visible to"
                " SGTM; treating it as having no members"
            )
            return []
        members = team["members"]
        logins.extend(node["login"] for node in members["nodes"])
        page_info = members.get("pageInfo") or {}
        if not page_info.get("hasNextPage"):
            return logins
        variables = {**variables, "cursor": page_info["endCursor"]}
