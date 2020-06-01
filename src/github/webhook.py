from operator import itemgetter

import src.github.graphql.client as graphql_client
from src.dynamodb.lock import dynamodb_lock
import src.github.controller as github_controller
from src.logger import logger
from src.github.models import PullRequestReviewComment, Review


# https://developer.github.com/v3/activity/events/types/#pullrequestevent
def _handle_pull_request_webhook(payload: dict):
    pull_request_id = payload["pull_request"]["node_id"]
    with dynamodb_lock(pull_request_id):
        pull_request = graphql_client.get_pull_request(pull_request_id)
        return github_controller.upsert_pull_request(pull_request)


# https://developer.github.com/v3/activity/events/types/#issuecommentevent
def _handle_issue_comment_webhook(payload: dict):
    action, issue, comment = itemgetter("action", "issue", "comment")(payload)

    issue_id = issue["node_id"]
    comment_id = comment["node_id"]
    with dynamodb_lock(issue_id):
        if action in ("created", "edited"):
            pull_request, comment = graphql_client.get_pull_request_and_comment(
                issue_id, comment_id
            )
            return github_controller.upsert_comment(pull_request, comment)
        elif action == "deleted":
            logger.info(f"Deleting comment {comment_id}")
            github_controller.delete_comment(comment_id)
        else:
            logger.info(f"Unknown action for issue_comment: {action}")


# https://developer.github.com/v3/activity/events/types/#pullrequestreviewevent
def _handle_pull_request_review_webhook(payload: dict):
    pull_request_id = payload["pull_request"]["node_id"]
    review_id = payload["review"]["node_id"]

    with dynamodb_lock(pull_request_id):
        pull_request, review = graphql_client.get_pull_request_and_review(
            pull_request_id, review_id
        )
        github_controller.upsert_review(pull_request, review)


# https://developer.github.com/v3/activity/events/types/#pullrequestreviewcommentevent
def _handle_pull_request_review_comment(payload: dict):
    """Handle when a pull request review comment is edited or removed.
    When comments are added it either hits:
        1 _handle_issue_comment_webhook (if the comment is on PR itself)
        2 _handle_pull_request_review_webhook (if the comment is on the "Files Changed" tab)
    Note that it hits (2) even if the comment is inline, and doesn't contain a review;
        in those cases Github still creates a review object for it.

    Unfortunately, this payload doesn't contain the node id of the review.
    Instead, it includes a separate, numeric id
    which is stored as `databaseId` on each GraphQL object.

    To get the review, we either:
        (1) query for the comment, and use the `review` edge in GraphQL.
        (2) Iterate through all reviews on the pull request, and find the one whose databaseId matches.
            See get_review_for_database_id()

    We do (1) for comments that were added or edited, but if a comment was just deleted, we have to do (2).

    See https://developer.github.com/v4/object/repository/#fields.
    """
    pull_request_id = payload["pull_request"]["node_id"]
    action = payload["action"]
    comment_id = payload["comment"]["node_id"]

    # This is NOT the node_id, but is a numeric string (the databaseId field).
    review_database_id = payload["comment"]["pull_request_review_id"]

    with dynamodb_lock(pull_request_id):
        if action in ("created", "edited"):
            pull_request, comment = graphql_client.get_pull_request_and_comment(
                pull_request_id, comment_id
            )
            if not isinstance(comment, PullRequestReviewComment):
                raise Exception(
                    f"Unexpected comment type {type(PullRequestReviewComment)} for pull request review"
                )
            review = Review.from_comment(comment)
        elif action == "deleted":
            pull_request = graphql_client.get_pull_request(pull_request_id)
            found_review = graphql_client.get_review_for_database_id(
                pull_request_id, review_database_id
            )
            if found_review is None:
                # If we deleted the last comment from a review, Github might have deleted teh review.
                # If so, we should delete the Asana comment.
                github_controller.delete_comment(comment_id)
            else:
                review = found_review
        else:
            raise ValueError(f"Unexpected action: {action}")
        github_controller.upsert_review(pull_request, review)


# https://developer.github.com/v3/activity/events/types/#statusevent
def _handle_status_webhook(payload: dict):
    commit_id = payload["commit"]["node_id"]
    with dynamodb_lock(commit_id):
        pull_request = graphql_client.get_pull_request_for_commit(commit_id)
        return github_controller.upsert_pull_request(pull_request)


_events_map = {
    "pull_request": _handle_pull_request_webhook,
    "issue_comment": _handle_issue_comment_webhook,
    "pull_request_review": _handle_pull_request_review_webhook,
    "status": _handle_status_webhook,
    "pull_request_review_comment": _handle_pull_request_review_comment,
}


def handle_github_webhook(event_type, payload):
    if event_type not in _events_map:
        logger.info(f"No handler for event type {event_type}")
        return

    logger.info(f"Received event type {event_type}!")
    return _events_map[event_type](payload)
