import src.asana.controller as asana_controller
import src.asana.helpers as asana_helpers
import src.github.logic as github_logic
import src.github.client as github_client
import src.aws.dynamodb_client as dynamodb_client
import src.aws.sqs_client as sqs_client
from src.config import (
    SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS,
)
from src.github.models import Comment, PullRequest, Review
from src.logger import logger


def upsert_pull_request(pull_request: PullRequest):
    pull_request_id = pull_request.id()
    task_id = dynamodb_client.get_asana_id_from_github_node_id(pull_request_id)
    if task_id is None:
        task_id = asana_controller.create_task(pull_request.repository_id())
        if task_id is None:
            logger.error(f"Failed to create task for pull request {pull_request_id}.")
            return

        logger.info(f"Task created for pull request {pull_request_id}: {task_id}")
        dynamodb_client.insert_github_node_to_asana_id_mapping(pull_request_id, task_id)
        asana_helpers.create_attachments(pull_request.body_html(), task_id)
        _add_asana_task_to_pull_request(pull_request, task_id)
    else:
        logger.info(
            f"Task found for pull request {pull_request_id}, updating task {task_id}"
        )
    asana_controller.update_task(
        pull_request,
        task_id,
        asana_helpers.task_followers_from_pull_request(pull_request),
    )


def _add_asana_task_to_pull_request(pull_request: PullRequest, task_id: str):
    owner = pull_request.repository_owner_handle()
    task_url = asana_helpers.task_url_from_task_id(task_id)
    new_body = github_logic.inject_metadata_into_pull_request_body(
        pull_request.body(), task_url=task_url, pr_url=pull_request.url()
    )
    github_client.edit_pr_description(
        owner, pull_request.repository_name(), pull_request.number(), new_body
    )

    # Update the PullRequest object to represent the new body, so we don't have
    # to query it again
    pull_request.set_body(new_body)


def upsert_comment(pull_request: PullRequest, comment: Comment, org_name: str):
    pull_request_id = pull_request.id()
    task_id = dynamodb_client.get_asana_id_from_github_node_id(pull_request_id)
    if task_id:
        if not comment.author().is_bot():
            asana_controller.upsert_github_comment_to_task(comment, task_id)
        # Comments can sometimes post-merge approve a PR, so we requeue a full sync via the "pull_request" event
        if github_logic.is_approval_comment_body(comment.body()):
            sqs_client.queue_full_sync(pull_request_id, org_name)
    else:
        logger.warning(
            f"Task not found for pull request {pull_request_id}. Queueing a new event..."
        )
        sqs_client.queue_full_sync(pull_request_id, org_name)


def upsert_review(pull_request: PullRequest, review: Review, org_name: str):
    pull_request_id = pull_request.id()
    task_id = dynamodb_client.get_asana_id_from_github_node_id(pull_request_id)
    if task_id:
        logger.info(
            f"Found task id {task_id} for pull_request {pull_request_id}. Adding review"
            " now."
        )
        if not review.author().is_bot():
            asana_controller.upsert_github_review_to_task(review, task_id)
        force_update_due_today = False
        if review.is_approval_or_changes_requested():
            # If this action was taken by a user that's marked for follow-up
            # review, we should leave the PR assignee as is so they can do the
            # follow-up.  Otherwise, reassign to the author so they can take
            # action on the PR.
            if (
                review.author().login()
                not in SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS
            ):
                assign_pull_request_to_author(pull_request)
                force_update_due_today = True
        asana_controller.update_task(
            pull_request,
            task_id,
            asana_helpers.task_followers_from_review(review),
            force_update_due_today=force_update_due_today,
        )
    else:
        logger.warning(
            f"Task not found for pull request {pull_request_id}. Queueing a new event..."
        )
        sqs_client.queue_full_sync(pull_request_id, org_name)


def assign_pull_request_to_author(pull_request: PullRequest):
    owner = pull_request.repository_owner_handle()
    new_assignee = pull_request.author_handle()
    github_client.set_pull_request_assignee(
        owner, pull_request.repository_name(), pull_request.number(), new_assignee
    )
    # so we don't have to re-query the PR
    pull_request.set_assignees([new_assignee])


def delete_comment(github_comment_id: str):
    asana_controller.delete_comment(github_comment_id)
