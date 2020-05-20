from typing import FrozenSet

# @GraphqlInPython
_full_review = """
fragment FullReview on PullRequestReview {
  id
  author {
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
      body
      url
      replyTo {
        id
      }
    }
  }
  url
}
"""

FullReview: FrozenSet[str] = frozenset([_full_review])
