from typing import FrozenSet

# @GraphqlInPython
# `expression` is a git revision expression such as "next-master:CODEOWNERS".
_get_repository_file_content = """
query GetRepositoryFileContent($owner: String!, $name: String!, $expression: String!) {
  repository(owner: $owner, name: $name) {
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
