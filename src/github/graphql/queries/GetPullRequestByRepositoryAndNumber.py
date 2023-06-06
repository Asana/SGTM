from typing import FrozenSet
from ..fragments import FullPullRequest, FullReview

# @GraphqlInPython
_get_pull_request_by_repository_and_number = """
query GetPullRequestByRepositoryAndNumber($repositoryId: ID!, $pullRequestNumber: Int!, $pullRequestId: ID, $getCheckSuites: Boolean = true) {
  repository: node(id: $repositoryId) {
    ... on Repository {
        pullRequest(number: $pullRequestNumber) {
          __typename
          ... on PullRequest {
            ...FullPullRequest
          }
        }
      }
  }
}
"""

GetPullRequestByRepositoryAndNumber: FrozenSet[str] = (
    frozenset([_get_pull_request_by_repository_and_number])
    | FullPullRequest
    | FullReview
)
