from typing import Tuple
from sgqlc.endpoint.http import HTTPEndpoint  # type: ignore
from src.config import GITHUB_API_KEY
from .schema import QUERIES
from src.github.models import comment_factory, PullRequest, Review, Comment


__url = "https://api.github.com/graphql"
__headers = {"Authorization": f"bearer {GITHUB_API_KEY}"}
__endpoint = HTTPEndpoint(__url, __headers)


def _execute_graphql_query(query_name: str, variables: dict) -> dict:
    if query_name not in QUERIES:
        raise KeyError(f"Unknown query {query_name}")
    query = QUERIES[query_name]
    response = __endpoint(query, variables)
    if "errors" in response:
        raise ValueError(f"Error in graphql query:\n{response }")
    data = response["data"]
    # if len(data.keys()) == 1:
    #     return data[list(data.keys())[0]]
    return data


def get_pull_request(pull_request_id: str) -> PullRequest:
    data = _execute_graphql_query("GetPullRequest", {"id": pull_request_id})
    return PullRequest(data["pullRequest"])


def get_pull_request_and_comment(
    pull_request_id: str, comment_id: str
) -> Tuple[PullRequest, Comment]:
    data = _execute_graphql_query(
        "GetPullRequestAndComment",
        {"pullRequestId": pull_request_id, "commentId": comment_id},
    )
    return PullRequest(data["pullRequest"]), comment_factory(data["comment"])


def get_pull_request_and_review(
    pull_request_id: str, review_id: str
) -> Tuple[PullRequest, Review]:
    data = _execute_graphql_query(
        "GetPullRequestAndReview",
        {"pullRequestId": pull_request_id, "reviewId": review_id},
    )
    return PullRequest(data["pullRequest"]), Review(data["review"])


def get_pull_request_for_commit(commit_id: str) -> PullRequest:
    data = _execute_graphql_query("GetPullRequestForCommit", {"id": commit_id})
    pull_request = data["commit"]["associatedPullRequests"]["edges"][0]["node"]
    return PullRequest(pull_request)

def get_review_for_database_id(pull_request_id: str, review_db_id: str):
    """Get the PullRequestReview given a pull request and the database id of the review.
    NOTE:
        @pull_request_id is a node id.
        @review_db_id is a databse id (it's numeric).

    Requires iterating through all reviews on the given pull request,
    because aside from using the legacy Github API I don't know how to query by databaseId.
    """
    data = _execute_graphql_query(
        "IterateReviews",
        {"pullRequestId": pull_request_id},
    )
    while data['node']['reviews']['edges']:
        try:
            match = next((e['node'] for e in data['node']['reviews']['edges'] if e['node']['databaseId'] == review_db_id))
            return Review(match)
        except StopIteration:
            # no matching reviews
            pass
    raise Exception(f"No review found for database id {review_db_id}")
