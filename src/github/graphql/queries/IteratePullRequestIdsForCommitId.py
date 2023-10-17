from typing import FrozenSet

# @GraphqlInPython
_iterate_pull_request_ids_for_commit_id = """
query IteratePullRequestIdsForCommitId($commitId: ID!, $cursor: String) {
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

IteratePullRequestIdsForCommitId: FrozenSet[str] = frozenset(
    [_iterate_pull_request_ids_for_commit_id]
)
