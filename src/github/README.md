# GitHub integration

## API

SGTM uses the GitHub API v4, as described [here, on the GitHub developer site](https://developer.github.com/v4/).  The API is implemented as a [GraphQL](https://graphql.org/learn/) service.

### Objects

The following objects from the GitHub API are of particular interest to SGTM:

* [User](https://developer.github.com/v4/object/user/)
* [PullRequest](https://developer.github.com/v4/object/pullrequest/)
  * [ReviewRequest](https://developer.github.com/v4/object/reviewrequest/)
  * [PullRequestReview](https://developer.github.com/v4/object/pullrequestreview/)
    * [PullRequestReviewComment](https://developer.github.com/v4/object/pullrequestreviewcomment/)
  * [IssueComment](https://developer.github.com/v4/object/issuecomment/)
