from typing import Tuple, FrozenSet, Optional
from sgqlc.endpoint.http import HTTPEndpoint  # type: ignore
from src.config import GITHUB_API_KEY
from src.github.models import comment_factory, PullRequest, Review, Comment
from .queries import (
    GetPullRequest,
    GetPullRequestByRepositoryAndNumber,
    GetPullRequestAndComment,
    GetPullRequestAndReview,
    IteratePullRequestsForCommit,
    IterateReviewsForPullRequest,
)


__url = "https://api.github.com/graphql"
__headers = {"Authorization": f"bearer {GITHUB_API_KEY}"}
__endpoint = HTTPEndpoint(__url, __headers)


def _execute_graphql_query(query: FrozenSet[str], variables: dict) -> dict:
    query_str = "\n".join(query)
    response = __endpoint(query_str, variables)
    if "errors" in response:
        raise ValueError(f"Error in graphql query:\n{response }")
    data = response["data"]
    # if len(data.keys()) == 1:
    #     return data[list(data.keys())[0]]
    return data


def get_pull_request(pull_request_id: str) -> PullRequest:
    data = _execute_graphql_query(GetPullRequest, {"pullRequestId": pull_request_id})
    return PullRequest(data["pullRequest"])


def get_pull_request_by_repository_and_number(
    repository_node_id: str, pull_request_number: int
) -> PullRequest:
    data = _execute_graphql_query(
        GetPullRequestByRepositoryAndNumber,
        {"repository": repository_node_id, "number": pull_request_number},
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


def get_pull_request_for_commit(commit_id: str) -> Optional[PullRequest]:
    """
    Every commit can be associated with more than one Pull Request. However, we are only
    interested in the Pull Requests where the most recent commit is the current commitId.

    We iterate through all Pull Requests associated with the commit, and return the first
    Pull Request where the most recent commit is the current commitId.
    """
    data = _execute_graphql_query(IteratePullRequestsForCommit, {"commitId": commit_id})

    def is_commit_last_commit_on_pull_request(pull_request_edge):
        last_commit_id = pull_request_edge["node"]["commits"]["nodes"][0]["commit"][
            "id"
        ]
        matches = last_commit_id == commit_id
        print("Matches: {} because {} ?= {}".format(matches, last_commit_id, commit_id))
        return matches

    print(data)
    pull_request_edges = data["commit"]["associatedPullRequests"]["edges"]
    while pull_request_edges:
        try:
            match = next(
                pull_request_edge["node"]["id"]
                for pull_request_edge in pull_request_edges
                if is_commit_last_commit_on_pull_request(pull_request_edge)
            )
            return get_pull_request(match)
        except StopIteration:
            data = _execute_graphql_query(
                IteratePullRequestsForCommit,
                {"commitId": commit_id, "cursor": pull_request_edges[-1]["cursor"]},
            )
            pull_request_edges = data["commit"]["associatedPullRequests"]["edges"]
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
    data = _execute_graphql_query(
        IterateReviewsForPullRequest, {"pullRequestId": pull_request_id}
    )
    review_edges = data["node"]["reviews"]["edges"]
    while review_edges:
        try:
            match = next(
                (
                    e["node"]
                    for e in review_edges
                    if e["node"]["databaseId"] == review_db_id
                )
            )
            return Review(match)
        except StopIteration:
            # no matching reviews, continue.
            data = _execute_graphql_query(
                IterateReviewsForPullRequest,
                {
                    "pullRequestId": pull_request_id,
                    "cursor": review_edges[-1]["cursor"],
                },
            )
            review_edges = data["node"]["reviews"]["edges"]
    return None
