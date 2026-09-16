from .FullReview import FullReview
from typing import FrozenSet

# @GraphqlInPython
_full_pull_request = """
fragment FullPullRequest on PullRequest {
  id
  headRefName
  headRefOid
  baseRefName
  baseRef {
    associatedPullRequests(states: OPEN, first: 1) {
      totalCount
    }
  }
  stack {
    baseRefName
  }
  body
  bodyHTML
  title
  author {
    login
  }
  closed
  merged
  isDraft
  isInMergeQueue
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
    defaultBranchRef {
      name
    }
  }
  reviewRequests(last: 100) {
    nodes {
      asCodeOwner
      requestedReviewer {
        ... on User {
          login
        }
        ... on Team {
          name
          slug
          combinedSlug
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
  reviews(last: 100) {
    nodes {
      ...FullReview
    }
  }
  comments(last: 20) {
    nodes {
      id
      databaseId
      author {
        login
      }
      publishedAt
      body
      bodyHTML
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
        oid
        committedDate
        statusCheckRollup {
          state
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
  files(first: 100) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      path
    }
  }
}
"""

FullPullRequest: FrozenSet[str] = frozenset([_full_pull_request]) | FullReview
