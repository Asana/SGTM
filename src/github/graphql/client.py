from typing import Tuple, FrozenSet, Optional
from sgqlc.endpoint.http import HTTPEndpoint  # type: ignore
from src.github.get_app_token import sgtm_github_auth
from src.github.models import comment_factory, PullRequest, Review, Comment
from .queries import (
    GetPullRequest,
    GetPullRequestByRepositoryAndNumber,
    GetPullRequestAndComment,
    GetPullRequestAndReview,
    GetRepository,
    IteratePullRequestIdsForCommitId,
    IterateReviewsForPullRequestId,
)

####################################################################################################
####### Core GraphQL Client helpers
####################################################################################################


__endpoint = sgtm_github_auth.get_graphql_endpoint()


def _execute_graphql_query(query: FrozenSet[str], variables: dict) -> dict:
    query_str = "\n".join(query)
    response = __endpoint(query_str, variables)
    if "errors" in response:
        raise ValueError(f"Error in graphql query:\n{response }")
    data = response["data"]
    # if len(data.keys()) == 1:
    #     return data[list(data.keys())[0]]
    return data


####################################################################################################
####### Specific queries
####################################################################################################


def get_pull_request(pull_request_id: str) -> PullRequest:
    data = _execute_graphql_query(GetPullRequest, {"pullRequestId": pull_request_id})
    return PullRequest(data["pullRequest"])


def get_pull_request_by_repository_and_number(
    repository_node_id: str, pull_request_number: int
) -> PullRequest:
    data = _execute_graphql_query(
        GetPullRequestByRepositoryAndNumber,
        {"repositoryId": repository_node_id, "pullRequestNumber": pull_request_number},
    )
    return PullRequest(data["repository"]["pullRequest"])


def get_pull_request_and_comment(
    pull_request_id: str, comment_id: str
) -> Tuple[PullRequest, Comment]:
    data = _execute_graphql_query(
        GetPullRequestAndComment,
        {"pullRequestId": pull_request_id, "commentId": comment_id},
    )
    return PullRequest(data["pullRequest"]), comment_factory(data["comment"])


def get_pull_request_and_review(
    pull_request_id: str, review_id: str
) -> Tuple[PullRequest, Review]:
    data = _execute_graphql_query(
        GetPullRequestAndReview,
        {"pullRequestId": pull_request_id, "reviewId": review_id},
    )
    return PullRequest(data["pullRequest"]), Review(data["review"])


def get_pull_request_for_commit_id(commit_id: str) -> Optional[PullRequest]:
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
        IteratePullRequestIdsForCommitId, {"commitId": commit_id}
    )["commit"]["associatedPullRequests"]["edges"]
    while pull_request_edges:
        try:
            match = next(
                (e["node"]["id"] for e in pull_request_edges if is_last_commit(e))
            )
            return get_pull_request(match)
        except StopIteration:
            pull_request_edges = _execute_graphql_query(
                IteratePullRequestIdsForCommitId,
                {
                    "commitId": commit_id,
                    "cursor": pull_request_edges[-1]["cursor"],
                },
            )["commit"]["associatedPullRequests"]["edges"]
    return None


def get_review_for_database_id(
    pull_request_id: str, review_db_id: str
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
        IterateReviewsForPullRequestId, {"pullRequestId": pull_request_id}
    )["node"]["reviews"]["edges"]
    while review_edges:
        try:
            match = next((e["node"] for e in review_edges if is_review(e)))
            return Review(match)
        except StopIteration:
            # no matching reviews, continue.
            review_edges = _execute_graphql_query(
                IterateReviewsForPullRequestId,
                {
                    "pullRequestId": pull_request_id,
                    "cursor": review_edges[-1]["cursor"],
                },
            )["node"]["reviews"]["edges"]
    return None


def get_repository(repository_id: str):
    data = _execute_graphql_query(GetRepository, {"repositoryId": repository_id})
    return data["repository"]
