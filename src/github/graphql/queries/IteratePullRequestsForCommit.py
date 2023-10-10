from typing import FrozenSet

# TODO: Handle multiple Pull Requests associated with one commit
# @GraphqlInPython
_iterate_pull_requests_for_commit = """
query IteratePullRequestsForCommit($commitId: ID!, $cursor: String) {
  commit: node(id: $commitId) {
    ... on Commit {
      associatedPullRequests(first: 20, after: $cursor) {
        edges {
          cursor
          node {
            ... on PullRequest {
              id
              commits(last: 1) {
                nodes {
                  commit {
                    id
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

IteratePullRequestsForCommit: FrozenSet[str] = frozenset(
    [_iterate_pull_requests_for_commit]
)
