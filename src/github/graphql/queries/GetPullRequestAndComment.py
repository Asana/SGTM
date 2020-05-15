from ..fragments import FullPullRequest, FullComment, FullReview

GetPullRequestAndComment: frozenset = (
    frozenset(
        [
            """
query GetPullRequestAndComment($pullRequestId: ID!, $commentId: ID!) {
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
        ]
    )
    | FullPullRequest
    | FullComment
    | FullReview
)
