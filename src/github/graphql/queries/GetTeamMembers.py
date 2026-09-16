from typing import FrozenSet

# @GraphqlInPython
_get_team_members = """
query GetTeamMembers($org: String!, $teamSlug: String!, $cursor: String) {
  organization(login: $org) {
    team(slug: $teamSlug) {
      members(first: 100, after: $cursor) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          login
        }
      }
    }
  }
}
"""

GetTeamMembers: FrozenSet[str] = frozenset([_get_team_members])
