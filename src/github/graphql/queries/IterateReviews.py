from typing import FrozenSet
from ..fragments import FullReview

# @GraphqlInPython
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

IterateReviews: FrozenSet[str] = frozenset(_iterate_reviews) | FullReview
