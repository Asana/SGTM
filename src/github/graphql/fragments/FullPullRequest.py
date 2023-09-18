from .FullReview import FullReview
from typing import FrozenSet

# @GraphqlInPython
_full_pull_request = """
fragment FullPullRequest on PullRequest {
  id
  baseRefName
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
        status {
          state
          contexts {
            context
            description
            state
          }
        }
        checkSuites(last: 20) {
          nodes {
            checkRuns(filterBy: {checkType: LATEST}, last: 20) {
              nodes {
                completedAt
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
