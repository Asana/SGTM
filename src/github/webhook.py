from typing import Optional
from operator import itemgetter
import time

import src.github.graphql.client as graphql_client
from src.dynamodb.lock import dynamodb_lock
import src.github.controller as github_controller
import src.github.logic as github_logic
from src.http import HttpResponse
from src.logger import logger
from src.github.models import PullRequestReviewComment, Review


# https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#pull_request
def _handle_pull_request_webhook(payload: dict) -> HttpResponse:
    pull_request_id = payload["pull_request"]["node_id"]
    pull_request = graphql_client.get_pull_request(pull_request_id)
    with dynamodb_lock(pull_request_id):
        pull_request = graphql_client.get_pull_request(pull_request_id)
        # maybe rerun stale checks on approved PR before attempting to automerge
        did_rerun_stale_required_checks = (
            github_logic.maybe_rerun_stale_checks_on_approved_pull_request(pull_request)
        )
        # a label change will trigger this webhook, so it may trigger automerge
        github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
            pull_request, did_rerun_stale_required_checks
        )
        github_logic.maybe_add_automerge_warning_comment(pull_request)
        github_controller.upsert_pull_request(pull_request)
        return HttpResponse("200")


# https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#issue_comment
def _handle_issue_comment_webhook(payload: dict) -> HttpResponse:
    action, issue, comment = itemgetter("action", "issue", "comment")(payload)

    issue_id = issue["node_id"]  # issue_id can be pull_request_id
    comment_id = comment["node_id"]
    logger.info(f"issue: {issue_id}, comment: {comment_id}")

    if action == "created" or action == "edited":
        with dynamodb_lock(comment_id):
            pull_request, comment = graphql_client.get_pull_request_and_comment(
                issue_id, comment_id
            )
            github_controller.upsert_comment(pull_request, comment)
        return HttpResponse("200")

    if action == "deleted":
        logger.info(f"Deleting comment {comment_id}")
        with dynamodb_lock(comment_id):
            github_controller.delete_comment(comment_id)
        return HttpResponse("200")

    error_text = f"Unknown action for issue_comment: {action}"
    logger.error(error_text)
    return HttpResponse("400", error_text)


# https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#pull_request_review
def _handle_pull_request_review_webhook(payload: dict) -> HttpResponse:
    pull_request_id = payload["pull_request"]["node_id"]
    review_id = payload["review"]["node_id"]
    pull_request, review = graphql_client.get_pull_request_and_review(
        pull_request_id, review_id
    )
    with dynamodb_lock(pull_request_id):
        github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(pull_request)
        github_controller.upsert_review(pull_request, review)
    return HttpResponse("200")


# https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#pull_request_review_comment
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
    action = payload["action"]
    comment_id = payload["comment"]["node_id"]
    pull_request_id = payload["pull_request"]["node_id"]

    # This is NOT the node_id, but is a numeric string (the databaseId field).
    review_database_id = payload["comment"]["pull_request_review_id"]

    review: Optional[Review] = None

    if action == "created" or action == "edited":
        pull_request, comment = graphql_client.get_pull_request_and_comment(
            pull_request_id, comment_id
        )
        if not isinstance(comment, PullRequestReviewComment):
            raise Exception(
                f"Unexpected comment type {type(PullRequestReviewComment)} for pull"
                " request review"
            )
        review = Review.from_comment(comment)
    elif action == "deleted":
        review = graphql_client.get_review_for_database_id(
            pull_request_id, review_database_id
        )
    else:
        error_text = f"Unknown action for review_comment: {action}"
        logger.error(error_text)
        return HttpResponse("400", error_text)

    if review is None:
        # If a pull_request_review has only one comment that is deleted,
        # the review is deleted. This can change the approval status of the PR
        # if the deleted comment was part of a "changes requested" review.
        with dynamodb_lock(comment_id):
            github_controller.delete_comment(comment_id)
        return _handle_pull_request_webhook(payload)

    with dynamodb_lock(review.id()):
        github_controller.upsert_review(pull_request, review)
    return HttpResponse("200")


# https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#status
def _handle_status_webhook(payload: dict) -> HttpResponse:
    commit_id = payload["commit"]["node_id"]
    pull_request = graphql_client.get_pull_request_for_commit_id(commit_id)
    if pull_request is None:
        # This could happen for commits that get pushed outside of the normal
        # pull request flow. These should just be silently ignored.
        logger.warn(f"No pull request found for commit id {commit_id}")
        return HttpResponse("200")

    with dynamodb_lock(pull_request.id()):
        github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(pull_request)
        github_controller.upsert_pull_request(pull_request)
        return HttpResponse("200")


# https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#check_suite
def _handle_check_suite_webhook(payload: dict) -> HttpResponse:
    pull_requests = payload["check_suite"]["pull_requests"]
    if len(pull_requests) == 0:
        return HttpResponse("400", "No Pull Request Found")

    # TODO: How to handle multiple PRs?
    pull_request_number = pull_requests[0]["number"]
    repository_node_id = payload["repository"]["node_id"]

    pull_request = graphql_client.get_pull_request_by_repository_and_number(
        repository_node_id, pull_request_number
    )

    with dynamodb_lock(pull_request.id()):
        github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(pull_request)
        github_controller.upsert_pull_request(pull_request)
        return HttpResponse("200")


_events_map = {
    "pull_request": _handle_pull_request_webhook,
    "issue_comment": _handle_issue_comment_webhook,
    "pull_request_review": _handle_pull_request_review_webhook,
    "status": _handle_status_webhook,
    "pull_request_review_comment": _handle_pull_request_review_comment,
    "check_suite": _handle_check_suite_webhook,
}


def handle_github_webhook(event_type, payload) -> HttpResponse:
    if event_type not in _events_map:
        logger.info(f"No handler for event type {event_type}")
        return HttpResponse("501", f"No handler for event type {event_type}")

    logger.info(f"Received event type {event_type}!")
    # TEMPORARY: sleep for 2 seconds before handling any webhook. We're running
    # into an issue where the Github Webhook sends us a node_id, but when we
    # immediately query that id using the GraphQL API, we get back an error
    # "Could not resolve to a node with the global id of '<node_id>'". This is
    # an attempt to mitigate this issue temporarily by waiting a second to see
    # if Github's data consistency needs a bit of time (does not have
    # read-after-write consistency)
    time.sleep(2)
    return _events_map[event_type](payload)
