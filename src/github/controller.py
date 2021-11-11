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
            logger.error(f"No task id returned from create task {pull_request_id}")
            return

        logger.info(f"Task created for pull request {pull_request_id}: {task_id}")
        dynamodb_client.insert_github_node_to_asana_id_mapping(pull_request_id, task_id)
        asana_helpers.create_attachments(pull_request.body(), task_id)
        _add_asana_task_to_pull_request(pull_request, task_id)
    else:
        logger.info(
            f"Task found for pull request {pull_request_id}, updating task {task_id}"
        )
    asana_controller.update_task(pull_request, task_id)
    upsert_subtasks(pull_request, task_id)
    update_subtasks(pull_request, task_id)


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


def upsert_subtasks(pull_request: PullRequest, task_id: str) -> None:
    """
    Create subtasks for the reviewers.

    This is synchronized with dynamodb so we only create a subtask once for each reviewer.

    We go through the list of requested reviewers and check if they have a subtask created already.
    If not, we create the subtask.
    """
    for reviewer in pull_request.requested_reviewers():
        subtask_id = dynamodb_client.get_asana_id_from_two_github_node_ids(
            pull_request.id(), reviewer.id()
        )
        if subtask_id is None:
            created_subtask_id = asana_controller.create_review_subtask(
                pull_request, task_id, reviewer.login()
            )
            if created_subtask_id is None:
                # TODO: Handle this case
                logger.error(
                    f"No subtask id returned from create subtask {pull_request.id()}: {task_id}"
                )
                continue

            logger.info(
                f"Subtask created for pull request {pull_request.id()}: {task_id}: {created_subtask_id}"
            )
            dynamodb_client.insert_two_github_node_to_asana_id_mapping(
                pull_request.id(), reviewer.id(), created_subtask_id
            )


def update_subtasks(pull_request: PullRequest, task_id: str) -> None:
    """Syncs the subtasks based on latest version of the PR.

    Here we want to do three things:
        1. Sync updates to the PR name and other content to the subtask.
        2. Re-open, with note, subtasks that were completed since a new review has been requested.
        3. Close, with note, subtasks where reviewer has been removed.
    """
    for reviewer in pull_request.requested_reviewers():
        subtask_id = dynamodb_client.get_asana_id_from_two_github_node_ids(
            pull_request.id(), reviewer.id()
        )
        if subtask_id is None:
            # This should not happen as we should already have created subtasks for all
            # requested reviewers.
            # TODO: Handle this case
            logger.error(
                f"No subtask id returned for requested reviewer. PR {pull_request.id()} Reviewer: {reviewer.id()}"
            )
        asana_controller.update_subtask(pull_request, subtask_id)

    # TODO: Find tasks to be closed with comment.
    # TODO: Update the subtask title and task description if applicable.


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
        update_subtask_after_review(pull_request, review)


def update_subtask_after_review(pull_request: PullRequest, review: Review) -> None:
    subtask_id = dynamodb_client.get_asana_id_from_two_github_node_ids(
        pull_request.id(), review.author().id()
    )
    if subtask_id is None:
        # This happens if the review was made by a person not requested to review
        # TODO: Test this scenario and delete the print and logging statement.
        print("Review made by a person that was not requested to review")
        logger.info(
            f"Could not find subtask for author {review.author().id()} on PR {pull_request.id()}"
        )
    else:
        # Here we want to update the subtask.
        # TODO do we want to track this with dynamodb so this only gets executed once?
        asana_controller.update_subtask_after_review(pull_request, review, subtask_id)


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
