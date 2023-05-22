from .FullReview import FullReview
from typing import FrozenSet

# @GraphqlInPython
_full_pull_request = """
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
  isDraft
  mergedAt
  mergeable
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
        ... on Team {
          name
          members(last:20) {
            nodes {
              ... on User {
                login
              }
            }
          }
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
        statusCheckRollup {
          state
        }
        checkSuites(last: 20) {
          nodes {
            app {
              id
              databaseId
              name
            }
            conclusion
            checkRuns(filterBy: {checkType: LATEST}, last: 20) {
              nodes {
                id
                conclusion
                completedAt
                isRequired(pullRequestId: $id)
                name
                status
                databaseId
              }
            }
          }
        }
      }
    }
  }
  labels(last: 20) {
    nodes {
      name
    }
  }
}
"""

FullPullRequest: FrozenSet[str] = frozenset([_full_pull_request]) | FullReview
