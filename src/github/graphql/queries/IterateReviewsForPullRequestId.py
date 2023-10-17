from typing import FrozenSet
from ..fragments import FullReview

# @GraphqlInPython
_iterate_reviews_for_pull_request_id = """
query IterateReviewsForPullRequestId($pullRequestId: ID!, $cursor: String) {
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

IterateReviewsForPullRequestId: FrozenSet[str] = (
    frozenset([_iterate_reviews_for_pull_request_id]) | FullReview
)
