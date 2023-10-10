from typing import FrozenSet

# @GraphqlInPython
_full_status_check_rollup_context = """
fragment FullStatusCheckRollupContext on StatusCheckRollupContext {
  __typename
  ... on CheckRun {
    completedAt
    conclusion
    databaseId
    isRequired(pullRequestId: $id)
    name
  }
  ... on StatusContext {
    context
    createdAt
    isRequired(pullRequestId: $id)
    state
  }
}
"""

FullStatusCheckRollupContext: FrozenSet[str] = frozenset(
    [_full_status_check_rollup_context]
)
