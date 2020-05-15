from ..fragments import FullPullRequest, FullReview

GetPullRequestForCommit = """
query GetPullRequestForCommit($id: ID!) {
  commit: node(id: $id) {
    ... on Commit {
      associatedPullRequests(first: 1) {
        edges {
          node {
            ... on PullRequest {
                ...FullPullRequest
            }
          }
        }
      }
    }
  }
}

""" + FullPullRequest + FullReview
