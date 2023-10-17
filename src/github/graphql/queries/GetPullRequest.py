from typing import FrozenSet
from ..fragments import FullPullRequest, FullReview

# @GraphqlInPython
_get_pull_request = """
query GetPullRequest($pullRequestId: ID!) {
  pullRequest: node(id: $pullRequestId) {
    __typename
    ... on PullRequest {
      ...FullPullRequest
    }
  }
}
"""

GetPullRequest: FrozenSet[str] = (
    frozenset([_get_pull_request]) | FullPullRequest | FullReview
)
