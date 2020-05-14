from operator import itemgetter

import src.github.graphql.client as graphql_client
from src.dynamodb.lock import dynamodb_lock
import src.github.controller as github_controller
from src.logger import logger
from src.github.models import PullRequestReviewComment


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
            logger.info(f"Deleting comment {comment.id()}")
            github_controller.delete_comment(comment)
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
    # For when a comment on a review is edited or removed
    # XCXC: Will this fire when a comment is added to a pending review?
    pull_request_id = payload["pull_request"]["node_id"]
    comment_id = payload["comment"]["node_id"]
    action = payload['action']

    with dynamodb_lock(pull_request_id):
        pull_request, comment = graphql_client.get_pull_request_and_comment(
            pull_request_id, comment_id
        )
        if isinstance(comment, PullRequestReviewComment):
            if action in ('created', 'edited'):
                github_controller.upsert_review(pull_request, comment.review())
            elif action == 'deleted':
                github_controller.delete_comment(comment)
            else:
                raise Exception(f"Unknown action: {action}")
        else:
            raise Exception("Can't fetch review for a comment that isn't a PullRequestReviewComment")


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
    'pull_request_review_comment': _handle_pull_request_review_comment
}


def handle_github_webhook(event_type, payload):
    if event_type not in _events_map:
        logger.info(f"No handler for event type {event_type}")
        return

    logger.info(f"Received event type {event_type}!")
    return _events_map[event_type](payload)
