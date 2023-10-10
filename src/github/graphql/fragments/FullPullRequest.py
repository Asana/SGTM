from .FullReview import FullReview
from .FullStatusCheckRollupContext import (
    FullStatusCheckRollupContextById,
    FullStatusCheckRollupContextByNumber,
)
from typing import FrozenSet

# @GraphqlInPython
_full_pull_request_by_id = """
fragment FullPullRequestById on PullRequest {
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
          contexts(last: 20) {
            nodes {
              ...FullStatusCheckRollupContextById
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

_full_pull_request_by_number = """
fragment FullPullRequestByNumber on PullRequest {
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
          contexts(last: 20) {
            nodes {
              ...FullStatusCheckRollupContextByNumber
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

FullPullRequestById: FrozenSet[str] = (
    frozenset([_full_pull_request_by_id])
    | FullReview
    | FullStatusCheckRollupContextById
)

FullPullRequestByNumber: FrozenSet[str] = (
    frozenset([_full_pull_request_by_number])
    | FullReview
    | FullStatusCheckRollupContextByNumber
)
