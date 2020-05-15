FullComment = """
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
