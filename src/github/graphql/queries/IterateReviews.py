from ..fragments import FullReview

IterateReviews = (
    frozenset(
        [
            """
query IterateReviews($pullRequestId: ID!, $cursor: String) {
  node(id: $pullRequestId) {
    ... on PullRequest {
      reviews(first: 20, after: $cursor) {
        edges {
          cursor
          node {
            ...FullReview
            databaseId
          }
        }
      }
    }
  }
}

"""
        ]
    )
    | FullReview
)
