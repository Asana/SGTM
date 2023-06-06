from typing import FrozenSet

# @GraphqlInPython
_full_commit = """
fragment FullCommit on Commit {
    statusCheckRollup {
        state
    }
    checkSuites(last: 20) @include(if: $getCheckSuites) {
        nodes {
            checkRuns(filterBy: {checkType: LATEST}, last: 20) {
                nodes {
                    completedAt
                    databaseId
                    isRequired(pullRequestId: $pullRequestId, pullRequestNumber: $pullRequestNumber)
                }
            }
        }
    }
}
"""

FullCommit: FrozenSet[str] = frozenset([_full_commit])
