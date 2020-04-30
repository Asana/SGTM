from operator import itemgetter
import src.github.graphql.client as graphql_client
from src.dynamodb.lock import dynamodb_lock
from typing import Any, Dict
import src.github.controller as github_controller
from src.utils import httpResponse
from src.logger import logger


# https://developer.github.com/v3/activity/events/types/#pullrequestevent
def _handle_pull_request_webhook(payload: dict):
    pull_request_id = payload["pull_request"]["node_id"]
    with dynamodb_lock(pull_request_id):
        pull_request = graphql_client.get_pull_request(pull_request_id)
        github_controller.upsert_pull_request(pull_request)
        return httpResponse("200")


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
            github_controller.upsert_comment(pull_request, comment)
            return httpResponse("200")
        elif action == "deleted":
            error_text = "TODO: deleted action is not supported yet"
            logger.info(error_text)
            return httpResponse("501", error_text)
        else:
            error_text = f"Unknown action for issue_comment: {action}"
            logger.info(error_text)
            return httpResponse("400", error_text)


# https://developer.github.com/v3/activity/events/types/#pullrequestreviewevent
def _handle_pull_request_review_webhook(payload: dict):
    pull_request_id = payload["pull_request"]["node_id"]
    review_id = payload["review"]["node_id"]
    with dynamodb_lock(pull_request_id):
        pull_request, review = graphql_client.get_pull_request_and_review(
            pull_request_id, review_id
        )
        github_controller.upsert_review(pull_request, review)
        return httpResponse("200")


# https://developer.github.com/v3/activity/events/types/#statusevent
def _handle_status_webhook(payload: dict):
    commit_id = payload["commit"]["node_id"]
    with dynamodb_lock(commit_id):
        pull_request = graphql_client.get_pull_request_for_commit(commit_id)
        github_controller.upsert_pull_request(pull_request)
        return httpResponse("200")


_events_map = {
    "pull_request": _handle_pull_request_webhook,
    "issue_comment": _handle_issue_comment_webhook,
    "pull_request_review": _handle_pull_request_review_webhook,
    "status": _handle_status_webhook,
}


def handle_github_webhook(event_type, payload):
    if event_type not in _events_map:
        logger.info(f"No handler for event type {event_type}")
        return

    logger.info(f"Received event type {event_type}!")
    return _events_map[event_type](payload)
