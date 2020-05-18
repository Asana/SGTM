from ..fragments import FullPullRequest, FullReview

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

GetPullRequest: frozenset = frozenset(
    [_get_pull_request]
) | FullPullRequest | FullReview
