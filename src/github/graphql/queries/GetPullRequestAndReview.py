from typing import FrozenSet
from ..fragments import (
    FullPullRequestById,
    FullReview,
    FullStatusCheckRollupContextById,
)

# @GraphqlInPython
_get_pull_request_and_review = """
query GetPullRequestAndReview($pullRequestId: ID!, $reviewId: ID!) {
  pullRequest: node(id: $pullRequestId) {
    __typename
    ... on PullRequest {
      ...FullPullRequestById
    }
  }

  review: node(id: $reviewId) {
    __typename
    id
    ... on PullRequestReview {
      ...FullReview
    }
  }
}
"""

GetPullRequestAndReview: FrozenSet[str] = (
    frozenset([_get_pull_request_and_review])
    | FullPullRequestById
    | FullReview
    | FullStatusCheckRollupContextById
)
