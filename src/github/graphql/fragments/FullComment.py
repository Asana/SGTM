_full_comment = """
fragment FullComment on Comment {
  __typename
  id
  author {
    login
    ... on User {
      name
    }
  }
  body
}
"""

FullComment: frozenset = frozenset([_full_comment])
