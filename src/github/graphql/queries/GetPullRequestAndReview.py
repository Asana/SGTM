from ..fragments import FullPullRequest, FullReview

# @GraphqlInPython
_get_pull_request_and_review = """
query GetPullRequestAndReview($pullRequestId: ID!, $reviewId: ID!) {
  pullRequest: node(id: $pullRequestId) {
    __typename
    ... on PullRequest {
      ...FullPullRequest
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

GetPullRequestAndReview: frozenset = frozenset(
    [_get_pull_request_and_review]
) | FullPullRequest | FullReview
