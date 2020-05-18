from ..fragments import FullPullRequest, FullReview

_get_pull_request_for_commit = """
query GetPullRequestForCommit($id: ID!) {
  commit: node(id: $id) {
    ... on Commit {
      associatedPullRequests(first: 1) {
        edges {
          node {
            ... on PullRequest {
                ...FullPullRequest
            }
          }
        }
      }
    }
  }
}
"""

GetPullRequestForCommit: frozenset = frozenset(
    [_get_pull_request_for_commit]
) | FullPullRequest | FullReview
