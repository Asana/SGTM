"""
  @GraphqlInPython

  Ideally, we would import fragments into other fragments or queries.
  However, graphql does not natively support this.
  There are some libraries that might do what we need, but for now I'm using python files and importing dependencies.

  One issue: graphql will reject any query that contains duplicate fragments (i.e. the same name).
  This is a problem because if A imports B and C; and B and C both import D, then A will be a syntax error.
  So, we store the queries / fragments as sets, formed as a union of itself with all of its dependencies.
  At query time, we convert each set to a single string, with elements separated by new lines.
"""

from typing import FrozenSet

_full_comment = """
fragment FullComment on Comment {
  __typename
  id
  author {
    __typename
    login
    ... on User {
      name
    }
  }
  body
  bodyHTML
  ... on IssueComment {
    url
  }
  ... on PullRequestReviewComment {
    url
  }
}
"""

FullComment: FrozenSet[str] = frozenset([_full_comment])
