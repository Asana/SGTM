# TODO: This is shitty, but works. Make it better.
FRAGMENTS = {
    "FullPullRequest": """
    fragment FullPullRequest on PullRequest {
      id
      body
      bodyHTML
      title
      author {
        login
      }
      closed
      merged
      mergedAt
      url
      number
      repository {
        id
        name
        owner {
          login
        }
      }
      reviewRequests(last: 20) {
        nodes {
          requestedReviewer {
            ... on User {
              login
            }
          }
        }
      }
      reviews(last: 20) {
        nodes {
          ...FullReview
        }
      }
      comments(last: 20) {
        nodes {
          id
          author {
            login
          }
          publishedAt
          body
          url
        }
      }
      assignees(last: 20) {
        nodes {
          login
        }
      }
      commits(last: 1) {
        nodes {
          commit {
            status {
              state
            }
          }
        }
      }
    }
    """,
    "FullComment": """
    fragment FullComment on Comment {
      id
      author {
        login
        ... on User {
          name
        }
      }
      body
    }
    """,
    "FullReview": """
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
    """,
}

QUERIES = {
    "GetPullRequest": """
            query GetPullRequest($id: ID!) {
              pullRequest: node(id: $id) {
                __typename
                ... on PullRequest {
                  ...FullPullRequest
                }
              }
            }
        """
    + "\n"
    + FRAGMENTS["FullPullRequest"]
    + "\n"
    + FRAGMENTS["FullReview"],
    "GetComment": """
            query GetComment($id: ID!) {
              comment: node(id: $id) {
                __typename
                ... on Comment {
                  ...FullComment
                }
              }
            }
        """
    + "\n"
    + FRAGMENTS["FullComment"],
    "GetReview": """
            query GetReview($id: ID!) {
              review: node(id: $id) {
                __typename
                ... on PullRequestReview {
                  ...FullReview
                }
              }
            }
        """
    + "\n"
    + FRAGMENTS["FullReview"],
    "GetPullRequestAndComment": """
            query GetPullRequestAndComment($pullRequestId: ID!, $commentId: ID!) {
              pullRequest: node(id: $pullRequestId) {
                __typename
                ... on PullRequest {
                  ...FullPullRequest
                }
              }

              comment: node(id: $commentId) {
                __typename
                ... on Comment {
                  ...FullComment
                }
                ... on IssueComment {
                  url
                }
                ... on PullRequestReviewComment {
                  url
                  pullRequestReview {
                    ... FullReview
                  }
                }
              }
            }
        """
    + "\n"
    + FRAGMENTS["FullPullRequest"]
    + "\n"
    + FRAGMENTS["FullComment"]
    + "\n"
    + FRAGMENTS["FullReview"],
    "GetPullRequestAndReview": """
            query GetPullRequestAndReview($pullRequestId: ID!, $reviewId: ID!) {
              pullRequest: node(id: $pullRequestId) {
                __typename
                ... on PullRequest {
                  ...FullPullRequest
                }
              }

              review: node(id: $reviewId) {
                __typename
                id
                ... on PullRequestReview {
                  ...FullReview
                }
              }
            }
        """
    + "\n"
    + FRAGMENTS["FullPullRequest"]
    + "\n"
    + FRAGMENTS["FullReview"],
    "GetPullRequestForCommit": """
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
        """
    + "\n"
    + FRAGMENTS["FullPullRequest"]
    + "\n"
    + FRAGMENTS["FullReview"],
}
