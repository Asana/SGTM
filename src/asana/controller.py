from typing import Optional
from . import client as asana_client
from . import helpers as asana_helpers
from src.github.models import Comment, PullRequest, Review
from src.logger import logger
from src.dynamodb import client as dynamodb_client


def create_task(repository_id: str) -> Optional[str]:
    # TODO: Allow overrides with environment variables?
    project_id = dynamodb_client.get_asana_id_from_github_node_id(repository_id)
    if project_id is None:
        logger.warn(f"No project id found for repository id {repository_id}")
        return None
    else:
        return asana_client.create_task(project_id)


def update_task(pull_request: PullRequest, task_id: str):
    task_url = asana_helpers.task_url_from_task_id(task_id)
    pr_url = pull_request.url()
    logger.info(f"Updating task {task_url} for pull request {pr_url}")

    fields = asana_helpers.extract_task_fields_from_pull_request(pull_request)
    # TODO: extract attachments here...

    # TODO: Should extract_task_fields_from_pull_request be broken into two
    # methods, one for fields and one for followers?
    update_task_fields = {
        k: v
        for k, v in fields.items()
        if k in ("assignee", "name", "html_notes", "completed", "custom_fields")
    }
    asana_client.update_task(task_id, update_task_fields)
    asana_client.add_followers(task_id, fields["followers"])


def add_comment_to_task(comment: Comment, task_id: str):
    github_comment_id = comment.id()
    asana_comment_id = dynamodb_client.get_asana_id_from_github_node_id(
        github_comment_id
    )
    if asana_comment_id is None:
        logger.info(f"Adding comment {github_comment_id} to task {task_id}")
        asana_comment_id = asana_client.add_comment(
            task_id, asana_helpers.asana_comment_from_github_comment(comment)
        )
        dynamodb_client.insert_github_node_to_asana_id_mapping(
            github_comment_id, asana_comment_id
        )
    else:
        logger.info(f"Comment {github_comment_id} already synced to task {task_id}")


def add_review_to_task(review: Review, task_id: str):
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
        logger.info(f"Review {github_review_id} already synced to task {task_id}")
