from ..fragments import FullPullRequest, FullComment, FullReview

_get_pull_request_and_comment = """
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

GetPullRequestAndComment: frozenset = frozenset(
    [_get_pull_request_and_comment]
) | FullPullRequest | FullComment | FullReview
