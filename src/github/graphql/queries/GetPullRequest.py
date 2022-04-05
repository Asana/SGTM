from typing import FrozenSet
from ..fragments import FullPullRequest, FullReview

# @GraphqlInPython
_get_pull_request = """
query GetPullRequest($id: ID!) {
  pullRequest: node(id: $id) {
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
