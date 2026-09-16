from typing import FrozenSet

# @GraphqlInPython
_get_pull_request_files = """
query GetPullRequestFiles($pullRequestId: ID!, $cursor: String) {
  pullRequest: node(id: $pullRequestId) {
    __typename
    ... on PullRequest {
      files(first: 100, after: $cursor) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          path
        }
      }
    }
  }
}
"""

GetPullRequestFiles: FrozenSet[str] = frozenset([_get_pull_request_files])
