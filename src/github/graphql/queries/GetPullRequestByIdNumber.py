from typing import FrozenSet
from ..fragments import FullPullRequest, FullReview

# @GraphqlInPython
_get_pull_request_by_id_number = """
query GetPullRequestByIdNumber($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      __typename
      ... on PullRequest {
        ...FullPullRequest
      }
    }
  }
}
"""

GetPullRequestByIdNumber: FrozenSet[str] = frozenset(
    [_get_pull_request_by_id_number]
) | FullPullRequest | FullReview
