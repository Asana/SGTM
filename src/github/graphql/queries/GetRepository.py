from typing import FrozenSet

# @GraphqlInPython
_get_repository = """
query GetRepository($repositoryId: ID!) {
  repository: node($repositoryId: ID!) {
    ... on Repository {
      deleteBranchOnMerge
      defaultBranchRef{
        name
      }
    }
  }
}
"""

GetRepository: FrozenSet[str] = frozenset([_get_repository])
