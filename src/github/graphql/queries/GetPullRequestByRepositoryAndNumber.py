from typing import FrozenSet
from ..fragments import (
    FullPullRequestByNumber,
    FullReview,
    FullStatusCheckRollupContextByNumber,
)

# @GraphqlInPython
_get_pull_request_by_repository_and_number = """
query GetPullRequestByRepositoryAndNumber($repositoryId: ID!, $pullRequestNumber: Int!) {
  repository: node(id: $repositoryId) {
    ... on Repository {
        pullRequest(number: $pullRequestNumber) {
          __typename
          ... on PullRequest {
            ...FullPullRequestByNumber
          }
        }
      }
  }
}
"""

GetPullRequestByRepositoryAndNumber: FrozenSet[str] = (
    frozenset([_get_pull_request_by_repository_and_number])
    | FullPullRequestByNumber
    | FullReview
    | FullStatusCheckRollupContextByNumber
)
