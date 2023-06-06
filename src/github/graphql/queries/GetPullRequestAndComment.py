from typing import FrozenSet
from ..fragments import FullPullRequest, FullComment, FullReview

# @GraphqlInPython
_get_pull_request_and_comment = """
query GetPullRequestAndComment($pullRequestId: ID!, $commentId: ID!, $pullRequestNumber: Int, $getCheckSuites: Boolean = true) {
  pullRequest: node(id: $pullRequestId) {
    __typename
    ... on PullRequest {
      ...FullPullRequest
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
    | FullPullRequest
    | FullComment
    | FullReview
)
