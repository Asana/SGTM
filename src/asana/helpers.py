import re
from html import escape
from typing import Callable, Match, Optional, List
from src.asana.client import get_project_custom_fields
from src.dynamodb import client as dynamodb_client
from src.github.models import Comment, PullRequest, Review
from src.github import logic as github_logic
from src.logger import logger


def task_url_from_task_id(task_id: str) -> str:
    return f"https://app.asana.com/0/0/{task_id}"


def extract_task_fields_from_pull_request(pull_request: PullRequest) -> dict:
    return {
        "assignee": _task_assignee_from_pull_request(pull_request),
        "name": _task_name_from_pull_request(pull_request),
        "html_notes": _task_description_from_pull_request(pull_request),
        "completed": _task_completion_from_pull_request(pull_request),
        "followers": _task_followers_from_pull_request(pull_request),
        "custom_fields": _custom_fields_from_pull_request(pull_request)
    }


def _task_status_from_pull_request(pull_request: PullRequest) -> str:
    if not pull_request.closed():
        return "Open"
    elif pull_request.closed() and pull_request.merged():
        return "Merged"
    elif pull_request.closed() and not pull_request.merged():
        return "Closed"


def _build_status_from_pull_request(pull_request: PullRequest) -> str:
    return pull_request.build_status().capitalize()


_custom_fields_to_extract_map = {
    "PR Status": _task_status_from_pull_request,
    "Build": _build_status_from_pull_request
}


def _custom_fields_from_pull_request(pull_request: PullRequest):
    repository_id = pull_request.repository_id()
    project_id = dynamodb_client.get_asana_id_from_github_node_id(repository_id)

    if project_id is None:
        logger.info(
            f"Task not found for pull request {pull_request.id()}. Running a full sync!"
        )
        # TODO: Full sync
        return {}
    else:
        custom_field_settings = list(get_project_custom_fields(project_id))
        data = {}
        for custom_field_name, action in _custom_fields_to_extract_map.items():
            custom_field_id = _get_custom_field_id(custom_field_name, custom_field_settings)
            enum_option_id = _get_custom_field_enum_option_id(
                custom_field_name, action(pull_request), custom_field_settings
            )
            if custom_field_id and enum_option_id:
                data[custom_field_id] = enum_option_id

        return data


def _get_custom_field_id(custom_field_name: str, custom_field_settings: List[dict]) -> Optional[str]:
    filtered_gid = [
        custom_field_setting['gid'] for custom_field_setting in custom_field_settings
        if custom_field_setting['custom_field']['name'] == custom_field_name
    ]
    return filtered_gid[0] if filtered_gid else None


def _get_custom_field_enum_option_id(custom_field_name: str, enum_option_name: str, custom_field_settings: List[dict]) -> Optional[str]:
    filtered_enum_options = [
        custom_field_setting['custom_field']['enum_options'] for custom_field_setting in custom_field_settings
        if custom_field_setting['custom_field']['name'] == custom_field_name
    ]

    if not filtered_enum_options:
        return None
    else:
        filtered_gid = [
            enum_option['gid'] for enum_option in filtered_enum_options[0]
            if enum_option['name'] == enum_option_name
        ]
        return filtered_gid[0] if filtered_gid else None


def _task_assignee_from_pull_request(pull_request: PullRequest) -> Optional[str]:
    assignee_handle = pull_request.assignee()
    return _asana_user_id_from_github_handle(assignee_handle)


def _asana_user_id_from_github_handle(github_handle: str) -> Optional[str]:
    return dynamodb_client.get_asana_domain_user_id_from_github_handle(github_handle)


def asana_author_from_github_author(author: dict) -> str:
    author_handle = author.get("login")
    author_name = author.get("name")
    if author_handle is not None:
        return _asana_url_from_github_handle(author_handle)
    elif author_name is not None:
        return f"{author_name} ({author_handle})"
    else:
        return ""


def _asana_url_from_github_handle(github_handle: str) -> str:
    user_id = _asana_user_id_from_github_handle(github_handle)
    return f'<a data-asana-gid="{user_id}"/>'


def _task_name_from_pull_request(pull_request: PullRequest) -> str:
    return "#{} - {}".format(pull_request.number(), pull_request.title())


def _transform_github_mentions_to_asana_mentions(text: str) -> str:
    def _replace_with_asana_mention(match: Match[str]) -> str:
        github_handle = match.group(1)
        asana_user_id = _asana_user_id_from_github_handle(github_handle)
        if asana_user_id is None:
            # Return the full matched string, including the "@"
            return match.group(0)
        else:
            return _asana_url_from_github_handle(github_handle)

    return re.sub(github_logic.GITHUB_MENTION_REGEX, _replace_with_asana_mention, text)


def asana_comment_from_github_comment(comment: Comment) -> str:
    asana_author = asana_author_from_github_author(comment.author())
    comment_text = _transform_github_mentions_to_asana_mentions(
        escape(comment.body(), quote=False)
    )
    return _wrap_in_tag("body")(
        _wrap_in_tag("strong")(f"{asana_author} commented:\n") + comment_text
    )


# https://developer.github.com/v4/reference/enum/pullrequestreviewstate/
_review_action_to_text_map = {
    "APPROVED": "approved",
    "CHANGES_REQUESTED": "requested changes",
    "COMMENTED": "reviewed",
    "DISMISSED": "reviewed",
}


def asana_comment_from_github_review(review: Review) -> str:
    asana_author = asana_author_from_github_author(review.author())
    review_action = _review_action_to_text_map.get(review.state(), "commented")
    review_body = _transform_github_mentions_to_asana_mentions(
        escape(review.body(), quote=False)
    )
    comment_texts = [comment.body() for comment in review.comments()]
    inline_comments = [
        _transform_github_mentions_to_asana_mentions(escape(comment_text, quote=False))
        for comment_text in comment_texts
    ]

    if not review_body and inline_comments:
        return _wrap_in_tag("body")(
            _wrap_in_tag("strong")(
                f"{asana_author} left inline comments:\n" + "\n\n".join(inline_comments)
            )
        )

    return _wrap_in_tag("body")(
        (
            (
                _wrap_in_tag("strong")(f"{asana_author} {review_action} :\n")
                + review_body
            )
            if review_body
            else _wrap_in_tag("strong")(f"{asana_author} {review_action}")
        )
        + (
            (
                _wrap_in_tag("strong")("\n\nand left inline comments:\n")
                + "\n\n".join(inline_comments)
            )
            if inline_comments
            else ""
        )
    )


def _task_description_from_pull_request(pull_request: PullRequest) -> str:
    url = pull_request.url()
    asana_author_url = _asana_url_from_github_handle(pull_request.author_handle())
    return _wrap_in_tag("body")(
        _wrap_in_tag("em")(
            "This is a one-way sync from GitHub to Asana. Do not edit this task or comment on it!"
        )
        + f"\n\n\uD83D\uDD17 {url}"
        + "\n✍️ "
        + asana_author_url
        + _wrap_in_tag("strong")("\n\nDescription:\n")
        + escape(pull_request.body(), quote=False)
    )


def _task_completion_from_pull_request(pull_request: PullRequest) -> bool:
    if not pull_request.closed():
        return False
    elif not pull_request.merged():
        return True
    elif github_logic.pull_request_approved_before_merging(pull_request):
        return True
    elif github_logic.pull_request_approved_after_merging(pull_request):
        return True
    else:
        return False


def _task_followers_from_pull_request(pull_request: PullRequest):
    return [
        _asana_user_id_from_github_handle(gh_handle)
        for gh_handle in github_logic.all_pull_request_participants(pull_request)
    ]


def _wrap_in_tag(tag_name: str) -> Callable[[str], str]:
    def inner(text: str) -> str:
        return f"<{tag_name}>{text}</{tag_name}>"

    return inner
