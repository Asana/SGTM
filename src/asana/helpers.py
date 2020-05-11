import re
from html import escape
from datetime import datetime, timedelta
from typing import Callable, Match, Optional, List, Dict
from src.dynamodb import client as dynamodb_client
from src.github.models import Comment, PullRequest, Review, User
from src.asana import client as asana_client
from src.github import logic as github_logic
from src.logger import logger


def task_url_from_task_id(task_id: str) -> str:
    """
    Transforms an Asana Task's object-id into an url referring to the task in the Asana app
    """
    if not task_id:
        raise ValueError("task_url_from_task_id requires a task_id")
    return f"https://app.asana.com/0/0/{task_id}"


def extract_task_fields_from_pull_request(pull_request: PullRequest) -> dict:
    """
    Extracts and transforms all relevant fields of a GitHub PullRequest into their corresponding
    equivalent fields, as relevant to an Asana Task
    :return: Returns the following fields: assignee, name, html_notes, followers and custom fields
    """
    return {
        "assignee": _task_assignee_from_pull_request(pull_request),
        "name": _task_name_from_pull_request(pull_request),
        "html_notes": _task_description_from_pull_request(pull_request),
        "completed": _task_completion_from_pull_request(pull_request),
        "followers": _task_followers_from_pull_request(pull_request),
        "custom_fields": _custom_fields_from_pull_request(pull_request),
    }


def default_due_date_str(reference_datetime: datetime = None) -> str:
    if reference_datetime is None:
        reference_datetime = datetime.now()

    tomorrow = reference_datetime + timedelta(hours=24)

    due_date = None
    if tomorrow.weekday() < 5:
        # weekday is 0-indexed at Monday, so 0,1,2,3,4 is Mon,Tues,Wed,Thurs,Fri
        # tomorrow is a weekday! Return it.
        due_date = tomorrow
    elif tomorrow.weekday() == 5:
        due_date = tomorrow + timedelta(
            hours=48
        )  # Tomorrow is Saturday, so add two more days to get to Monday
    else:
        due_date = tomorrow + timedelta(
            hours=24
        )  # Tomorrow is Sunday, so add one more day to get to Monday

    return due_date.strftime("%Y-%m-%d")


def _task_status_from_pull_request(pull_request: PullRequest) -> str:
    if not pull_request.closed():
        return "Open"
    elif pull_request.closed() and pull_request.merged():
        return "Merged"
    elif pull_request.closed() and not pull_request.merged():
        return "Closed"
    else:
        logger.error("Pull request is in an invalid state")
        return ""


def _build_status_from_pull_request(pull_request: PullRequest) -> Optional[str]:
    build_status = pull_request.build_status()
    return build_status.capitalize() if build_status is not None else None


_custom_fields_to_extract_map = {
    "PR Status": _task_status_from_pull_request,
    "Build": _build_status_from_pull_request,
}


def _custom_fields_from_pull_request(pull_request: PullRequest) -> Dict:
    """
    We currently expect the project to have two custom fields with its corresponding enum options:
        • PR Status: "Open", "Closed", "Merged"
        • Build: "Success", "Failure"

    TODO: Write script to set up an Asana project with these custom fields
    (https://app.asana.com/0/1149418478823393/1162588814088433/f)
    """
    repository_id = pull_request.repository_id()
    project_id = dynamodb_client.get_asana_id_from_github_node_id(repository_id)

    if project_id is None:
        logger.info(
            f"Task not found for pull request {pull_request.id()}. Running a full sync!"
        )
        # TODO: Full sync
        return {}
    else:
        custom_field_settings = list(asana_client.get_project_custom_fields(project_id))
        data = {}
        for custom_field_name, action in _custom_fields_to_extract_map.items():
            enum_option_name = action(pull_request)

            if enum_option_name:
                custom_field_id = _get_custom_field_id(
                    custom_field_name, custom_field_settings
                )
                enum_option_id = _get_custom_field_enum_option_id(
                    custom_field_name, enum_option_name, custom_field_settings
                )
                if custom_field_id and enum_option_id:
                    data[custom_field_id] = enum_option_id

        return data


def _get_custom_field_id(
    custom_field_name: str, custom_field_settings: List[dict]
) -> Optional[str]:
    filtered_gid = [
        custom_field_setting["custom_field"]["gid"]
        for custom_field_setting in custom_field_settings
        if custom_field_setting["custom_field"]["name"] == custom_field_name
    ]
    return filtered_gid[0] if filtered_gid else None


def _get_custom_field_enum_option_id(
    custom_field_name: str, enum_option_name: str, custom_field_settings: List[dict]
) -> Optional[str]:
    filtered_enum_options = [
        custom_field_setting["custom_field"]["enum_options"]
        for custom_field_setting in custom_field_settings
        if custom_field_setting["custom_field"]["name"] == custom_field_name
    ]

    if not filtered_enum_options:
        return None
    else:
        filtered_gid = [
            enum_option["gid"]
            for enum_option in filtered_enum_options[0]
            if enum_option["name"] == enum_option_name and enum_option["enabled"]
        ]
        return filtered_gid[0] if filtered_gid else None


def _task_assignee_from_pull_request(pull_request: PullRequest) -> Optional[str]:
    assignee_handle = pull_request.assignee()
    return _asana_user_id_from_github_handle(assignee_handle)


def _asana_user_id_from_github_handle(github_handle: str) -> Optional[str]:
    return dynamodb_client.get_asana_domain_user_id_from_github_handle(github_handle)


def _asana_display_name_for_github_user(github_user: User) -> str:
    """
        Retrieves a display name for a GitHub user that is usable in Asana. If the GitHub user is known by SGTM to
        be an Asana user, then an Asana user URL will be returned, otherwise the display name will be of the form:
                GitHub user 'David Brandt (padresmurfa)'
            or  Github user 'padresmurfa'
    """
    asana_author_user = _asana_user_url_from_github_user_handle(github_user.login())
    if asana_author_user is not None:
        return asana_author_user
    # default to returning GitHub user details, if Asana user details are not available
    if github_user.name() is not None and github_user.name():
        return f"GitHub user '{github_user.name()} ({github_user.login()})'"
    return f"GitHub user '{github_user.login()}'"


def _asana_user_url_from_github_user_handle(github_handle: str) -> Optional[str]:
    user_id = _asana_user_id_from_github_handle(github_handle)
    if user_id is None:
        return None
    return f'<a data-asana-gid="{user_id}"/>'


def _task_name_from_pull_request(pull_request: PullRequest) -> str:
    return "#{} - {}".format(pull_request.number(), pull_request.title())


def _transform_github_mentions_to_asana_mentions(text: str) -> str:
    def _github_mention_to_asana_mention(match: Match[str]) -> str:
        github_handle = match.group(1)
        asana_user_id = _asana_user_id_from_github_handle(github_handle)
        if asana_user_id is None:
            # Return the full matched string, including the "@"
            return match.group(0)
        else:
            asana_user_url = _asana_user_url_from_github_user_handle(github_handle)
            if asana_user_url is None:
                return github_handle
            return asana_user_url

    return re.sub(
        github_logic.GITHUB_MENTION_REGEX, _github_mention_to_asana_mention, text
    )


def asana_comment_from_github_comment(comment: Comment) -> str:
    """
    Extracts the GitHub author and comment text from a GitHub Comment, and transforms them into
    a suitable html comment string for Asana. This will involve looking up the GitHub author in
    DynamoDb to determine the Asana domain user id of the comment author and any @mentioned
    GitHub users.
    """
    github_author = comment.author()
    display_name = _asana_display_name_for_github_user(github_author)
    comment_text = _transform_github_mentions_to_asana_mentions(
        escape(comment.body(), quote=False)
    )
    return _wrap_in_tag("body")(
        _wrap_in_tag("A", {"HREF": comment.url()})(f"{display_name} commented:\n") +
        comment_text
    )


# https://developer.github.com/v4/reference/enum/pullrequestreviewstate/
_review_action_to_text_map = {
    "APPROVED": "approved",
    "CHANGES_REQUESTED": "requested changes",
    "COMMENTED": "reviewed",
    "DISMISSED": "reviewed",
}


def asana_comment_from_github_review(review: Review) -> str:
    """
    Extracts the GitHub author and comments from a GitHub Review, and transforms them into
    a suitable html comment string for Asana. This will involve looking up the GitHub author in
    DynamoDb to determine the Asana domain user id of the review author and any @mentioned GitHub
    users.
    """
    user_display_name = _asana_display_name_for_github_user(review.author())
    review_action = _review_action_to_text_map.get(review.state(), "commented")
    review_body = _transform_github_mentions_to_asana_mentions(
        escape(review.body(), quote=False)
    )
    comment_texts = [comment.body() for comment in review.comments()]
    inline_comments = [
        _transform_github_mentions_to_asana_mentions(escape(comment_text, quote=False))
        for comment_text in comment_texts
    ]

    return _wrap_in_tag("body")(
        (
            (
                _wrap_in_tag("strong")(f"{user_display_name} {review_action} :\n")
                + review_body
            )
            if review_body
            else _wrap_in_tag("strong")(f"{user_display_name} {review_action}")
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
    github_author = pull_request.author()
    author = _asana_user_url_from_github_user_handle(github_author.login())
    if author is None:
        author = _asana_display_name_for_github_user(github_author)
    return _wrap_in_tag("body")(
        _wrap_in_tag("em")(
            "This is a one-way sync from GitHub to Asana. Do not edit this task or comment on it!"
        )
        + f"\n\n\uD83D\uDD17 {url}"
        + "\n✍️ "
        + author
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
        if _asana_user_id_from_github_handle(gh_handle) is not None
    ]


def _wrap_in_tag(tag_name: str, attrs: Optional[dict] = None) -> Callable[[str], str]:
    # This will always start with a blank space, so it's separate from the tag name.
    attrs = ''.join(f" {k}={escape(v)}" for k, v in attrs.items())

    def inner(text: str) -> str:
        return f"<{tag_name}{attrs}>{text}</{tag_name}>"

    return inner
