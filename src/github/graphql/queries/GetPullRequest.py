from ..fragments import FullPullRequest, FullReview

GetPullRequest = (
    set(
        [
            """
query GetPullRequest($id: ID!) {
  pullRequest: node(id: $id) {
    __typename
    ... on PullRequest {
      ...FullPullRequest
    }
  }
}

"""
        ]
    )
    | FullPullRequest
    | FullReview
)
