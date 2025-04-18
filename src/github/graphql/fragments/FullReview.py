from typing import FrozenSet
from .FullComment import FullComment

# @GraphqlInPython
_full_review = """
fragment FullReview on PullRequestReview {
  id
  author {
    __typename
    login
    ... on User {
      name
    }
  }
  body
  submittedAt
  state
  comments(last: 20) {
    nodes {
      ...FullComment
    }
  }
  url
}
"""

FullReview: FrozenSet[str] = frozenset([_full_review]) | FullComment
