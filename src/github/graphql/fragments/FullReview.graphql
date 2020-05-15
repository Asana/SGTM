fragment FullReview on PullRequestReview {
  id
  author {
    login
    ... on User {
      name
    }
  }
  body
  submittedAt
  state
  comments(last: 20) {
    nodes {
      body
      url
    }
  }
  url
}