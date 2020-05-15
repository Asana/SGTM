from ..fragments import FullPullRequest, FullReview


GetPullRequestAndReview = set(["""
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

"""]) | FullPullRequest | FullReview
