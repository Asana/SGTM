from typing import FrozenSet

# @GraphqlInPython
_full_status_check_rollup_context_by_id = """
fragment FullStatusCheckRollupContextById on StatusCheckRollupContext {
  __typename
  ... on CheckRun {
    completedAt
    conclusion
    databaseId
    isRequired(pullRequestId: $pullRequestId)
    name
  }
  ... on StatusContext {
    context
    createdAt
    isRequired(pullRequestId: $pullRequestId)
    state
  }
}
"""

__full_status_check_rollup_context_by_number = """
fragment FullStatusCheckRollupContextById on StatusCheckRollupContext {
  __typename
  ... on CheckRun {
    completedAt
    conclusion
    databaseId
    isRequired(pullRequestNumber: $pullRequestNumber)
    name
  }
  ... on StatusContext {
    context
    createdAt
    isRequired(pullRequestNumber: $pullRequestNumber)
    state
  }
}
"""

FullStatusCheckRollupContextById: FrozenSet[str] = frozenset(
    [_full_status_check_rollup_context_by_id]
)

FullStatusCheckRollupContextByNumber: FrozenSet[str] = frozenset(
    [__full_status_check_rollup_context_by_number]
)
