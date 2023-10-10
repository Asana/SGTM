from typing import FrozenSet
from ..fragments import (
    FullPullRequestById,
    FullComment,
    FullReview,
    FullStatusCheckRollupContextById,
)

# @GraphqlInPython
_get_pull_request_and_comment = """
query GetPullRequestAndComment($pullRequestId: ID!, $commentId: ID!) {
  pullRequest: node(id: $pullRequestId) {
    __typename
    ... on PullRequest {
      ...FullPullRequestById
    }
  }

  comment: node(id: $commentId) {
    ... on Comment {
      ...FullComment
    }
    ... on IssueComment {
      url
    }
    ... on PullRequestReviewComment {
      url
      pullRequestReview {
        ... FullReview
      }
    }
  }
}
"""

GetPullRequestAndComment: FrozenSet[str] = (
    frozenset([_get_pull_request_and_comment])
    | FullPullRequestById
    | FullComment
    | FullReview
    | FullStatusCheckRollupContextById
)
