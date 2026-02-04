from typing import List, Optional

import src.asana.client as asana_client
import src.asana.helpers as asana_helpers
import src.asana.logic as asana_logic
import src.aws.dynamodb_client as dynamodb_client
from src.config import SGTM_FEATURE__AUTOCOMPLETE_ENABLED
from src.github.models import Comment, PullRequest, Review
from src.logger import logger


def create_task(repository_id: str) -> Optional[str]:
    project_id = dynamodb_client.get_asana_id_from_github_node_id(repository_id)
    if project_id is None:
        logger.warning(f"No project id found for repository id {repository_id}")
        return None
    else:
        due_date_str = asana_helpers.default_due_date_str()
        return asana_client.create_task(project_id, due_date_str=due_date_str)


def update_task(
    pull_request: PullRequest,
    task_id: str,
    followers: List[str],
    force_update_due_today: bool = False,
):
    task_url = asana_helpers.task_url_from_task_id(task_id)
    pr_url = pull_request.url()
    logger.info(f"Updating task {task_url} for pull request {pr_url}")

    update_task_fields = asana_helpers.extract_task_fields_from_pull_request(
        pull_request
    )
    task = asana_client.get_task(task_id)
    new_due_on = (
        asana_helpers.today_str()
        if force_update_due_today
        else _new_due_on_or_none(task, update_task_fields)
    )
    if new_due_on is not None:
        update_task_fields["due_on"] = new_due_on

    logger.info(f"Updating task {task_id} with fields: {update_task_fields}")
    asana_client.update_task(task_id, update_task_fields)
    # Add followers is optional because Asana should automatically add followers
    # if the body contains well-formatted data-asana-gid fields. Also bots can sometimes create comments,
    # reviews, and PRs which may or may not be included in the github handle to asana id mappings
    if len(followers) > 0:
        asana_client.add_followers(task_id, followers)
    maybe_complete_tasks_on_merge(pull_request)


def _new_due_on_or_none(task: dict, update_task_fields: dict) -> Optional[str]:
    today = asana_helpers.today_str()

    if task.get("due_on") and task["due_on"] >= today:
        # don't update due dates that aren't stale
        return None
    elif (task.get("assignee") or {}).get("gid") != update_task_fields.get("assignee"):
        # if the task is switching assignees, update the due date to today
        return today
    return None


def maybe_complete_tasks_on_merge(pull_request: PullRequest):
    if asana_logic.should_autocomplete_tasks_on_merge(pull_request):
        task_ids_to_complete_on_merge = asana_helpers.get_linked_task_ids(pull_request)
        logger.info(f"Task IDs to complete on merge: {task_ids_to_complete_on_merge}")
        for complete_on_merge_task_id in task_ids_to_complete_on_merge:
            try:
                asana_client.complete_task(complete_on_merge_task_id)
                logger.info(
                    f"Successfully completed Asana task {complete_on_merge_task_id} for merged PR {pull_request.url()}"
                )
            except Exception as e:
                task_url = asana_helpers.task_url_from_task_id(
                    complete_on_merge_task_id
                )
                logger.error(
                    f"Failed to complete Asana task {complete_on_merge_task_id} "
                    f"({task_url}) for PR {pull_request.url()}. Error: {str(e)}"
                )
    else:
        logger.info(
            f"Pull Request did not autocomplete linked tasks. One of the following conditions was not met: "
            f"{SGTM_FEATURE__AUTOCOMPLETE_ENABLED}, {pull_request.merged()}, {pull_request.labels()}"
        )


def upsert_github_comment_to_task(comment: Comment, task_id: str):
    github_comment_id = comment.id()
    asana_comment_id = dynamodb_client.get_asana_id_from_github_node_id(
        github_comment_id
    )
    if asana_comment_id is None:
        logger.info(f"Adding comment {github_comment_id} to task {task_id}")

        asana_helpers.create_attachments(comment.body_html(), task_id)

        asana_comment_id = asana_client.add_comment(
            task_id, asana_helpers.asana_comment_from_github_comment(comment)
        )
        dynamodb_client.insert_github_node_to_asana_id_mapping(
            github_comment_id, asana_comment_id
        )
    else:
        logger.info(
            f"Comment {github_comment_id} already synced to task {task_id}. Updating."
        )
        asana_client.update_comment(
            asana_comment_id, asana_helpers.asana_comment_from_github_comment(comment)
        )

    # Optionally add followers from the comment body
    followers = asana_helpers.task_followers_from_comment(comment)
    if len(followers) > 0:
        asana_client.add_followers(task_id, followers)


def upsert_github_review_to_task(review: Review, task_id: str):
    github_review_id = review.id()
    asana_comment_id = dynamodb_client.get_asana_id_from_github_node_id(
        github_review_id
    )
    if asana_comment_id is None:
        logger.info(f"Adding review {github_review_id} to task {task_id}")
        asana_comment_id = asana_client.add_comment(
            task_id, asana_helpers.asana_comment_from_github_review(review)
        )
        dynamodb_client.insert_github_node_to_asana_id_mapping(
            github_review_id, asana_comment_id
        )
    else:
        logger.info(
            f"Review {github_review_id} already synced to task {task_id}. Updating."
        )
        asana_client.update_comment(
            asana_comment_id, asana_helpers.asana_comment_from_github_review(review)
        )

    dynamodb_client.bulk_insert_github_node_to_asana_id_mapping(
        [(c.id(), asana_comment_id) for c in review.comments()]
    )


def delete_comment(github_comment_id: str):
    asana_comment_id = dynamodb_client.get_asana_id_from_github_node_id(
        github_comment_id
    )
    if asana_comment_id is not None:
        asana_client.delete_comment(asana_comment_id)
