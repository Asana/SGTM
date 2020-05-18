from ..fragments import FullReview

_iterate_reviews = """
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

IterateReviews: frozenset = frozenset(_iterate_reviews) | FullReview
