from typing import FrozenSet
from ..fragments import FullPullRequest, FullReview

# @GraphqlInPython
_get_pull_request_by_id_number = """
query GetPullRequestByRepositoryAndNumber($repository: ID!, $number: Int!) {
  repository: node(id: $repository) {
    ... on Repository {
        pullRequest(number: $number) {
          __typename
          ... on PullRequest {
            ...FullPullRequest
          }
        }
      }
  }
}
"""

GetPullRequestByRepositoryAndNumber: FrozenSet[str] = frozenset(
    [_get_pull_request_by_id_number]
) | FullPullRequest | FullReview
