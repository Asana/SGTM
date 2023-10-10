from typing import FrozenSet
from ..fragments import (
    FullPullRequestById,
    FullReview,
    FullStatusCheckRollupContextById,
)

# @GraphqlInPython
_get_pull_request = """
query GetPullRequest($pullRequestId: ID!) {
  pullRequest: node(id: $pullRequestId) {
    __typename
    ... on PullRequest {
      ...FullPullRequestById
    }
  }
}
"""

GetPullRequest: FrozenSet[str] = (
    frozenset([_get_pull_request])
    | FullPullRequestById
    | FullReview
    | FullStatusCheckRollupContextById
)
