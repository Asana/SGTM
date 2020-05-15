from ..fragments import FullPullRequest, FullReview

GetPullRequest = """
query GetPullRequest($id: ID!) {
  pullRequest: node(id: $id) {
    __typename
    ... on PullRequest {
      ...FullPullRequest
    }
  }
}

""" + FullPullRequest + FullReview
