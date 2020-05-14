import src.dynamodb.client as dynamodb_client
import src.asana.controller as asana_controller
from . import logic as github_logic
from . import client as github_client
import src.asana.helpers as asana_helpers
from src.github.models import Comment, PullRequest, Review
from src.logger import logger


def upsert_pull_request(pull_request: PullRequest):
    pull_request_id = pull_request.id()
    task_id = dynamodb_client.get_asana_id_from_github_node_id(pull_request_id)
    if task_id is None:
        task_id = asana_controller.create_task(pull_request.repository_id())
        if task_id is None:
            # TODO: Handle this case
            return

        logger.info(f"Task created for pull request {pull_request_id}: {task_id}")
        dynamodb_client.insert_github_node_to_asana_id_mapping(pull_request_id, task_id)
        _add_asana_task_to_pull_request(pull_request, task_id)
    else:
        logger.info(
            f"Task found for pull request {pull_request_id}, updating task {task_id}"
        )
    asana_controller.update_task(pull_request, task_id)


def _add_asana_task_to_pull_request(pull_request: PullRequest, task_id: str):
    owner = pull_request.repository_owner_handle()
    task_url = asana_helpers.task_url_from_task_id(task_id)
    new_body = github_logic.inject_asana_task_into_pull_request_body(
        pull_request.body(), task_url
    )
    github_client.edit_pr_description(
        owner, pull_request.repository_name(), pull_request.number(), new_body
    )

    # Update the PullRequest object to represent the new body, so we don't have
    # to query it again
    pull_request.set_body(new_body)


def upsert_comment(pull_request: PullRequest, comment: Comment):
    pull_request_id = pull_request.id()
    task_id = dynamodb_client.get_asana_id_from_github_node_id(pull_request_id)
    if task_id is None:
        logger.info(
            f"Task not found for pull request {pull_request_id}. Running a full sync!"
        )
        # TODO: Full sync
    else:
        asana_controller.upsert_github_comment_to_task(comment, task_id)
        asana_controller.update_task(pull_request, task_id)


def upsert_review(pull_request: PullRequest, review: Review):
    pull_request_id = pull_request.id()
    task_id = dynamodb_client.get_asana_id_from_github_node_id(pull_request_id)
    if task_id is None:
        logger.info(
            f"Task not found for pull request {pull_request_id}. Running a full sync!"
        )
        # TODO: Full sync
    else:
        logger.info(
            f"Found task id {task_id} for pull_request {pull_request_id}. Adding review now."
        )
        asana_controller.upsert_github_review_to_task(review, task_id)
        if review.is_approval_or_changes_requested():
            assign_pull_request_to_author(pull_request)
        asana_controller.update_task(pull_request, task_id)


def assign_pull_request_to_author(pull_request: PullRequest):
    owner = pull_request.repository_owner_handle()
    new_assignee = pull_request.author_handle()
    github_client.set_pull_request_assignee(
        owner, pull_request.repository_name(), pull_request.number(), new_assignee
    )
    # so we don't have to re-query the PR
    pull_request.set_assignees([new_assignee])


def delete_comment(comment: Comment):
    asana_controller.delete_comment(comment)
