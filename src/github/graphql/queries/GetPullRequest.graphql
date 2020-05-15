query GetPullRequest($id: ID!) {
  pullRequest: node(id: $id) {
    __typename
    ... on PullRequest {
      ...FullPullRequest
    }
  }
}