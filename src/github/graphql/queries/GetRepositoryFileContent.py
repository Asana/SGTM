from typing import FrozenSet

# @GraphqlInPython
# `expression` is a git revision expression such as "next-master:CODEOWNERS" and
# `ref` the qualified name of the same ref ("refs/heads/next-master"), so a
# missing file can be told apart from a branch that does not exist.
_get_repository_file_content = """
query GetRepositoryFileContent($owner: String!, $name: String!, $ref: String!, $expression: String!) {
  repository(owner: $owner, name: $name) {
    ref(qualifiedName: $ref) {
      id
    }
    object(expression: $expression) {
      __typename
      ... on Blob {
        text
        isTruncated
      }
    }
  }
}
"""

GetRepositoryFileContent: FrozenSet[str] = frozenset([_get_repository_file_content])
