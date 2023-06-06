from typing import FrozenSet
from ..fragments import FullPullRequest, FullReview

# @GraphqlInPython
_get_pull_request_for_commit = """
query GetPullRequestForCommit($commitId: ID!, $pullRequestId: ID, $pullRequestNumber: Int, $getCheckSuites: Boolean = false) {
  commit: node(id: $commitId) {
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

GetPullRequestForCommit: FrozenSet[str] = (
    frozenset([_get_pull_request_for_commit]) | FullPullRequest | FullReview
)
