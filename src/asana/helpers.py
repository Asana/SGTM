import re
from html import escape
from typing import Callable, Match, Optional
import src.dynamodb.client as dynamodb_client
from src.github.models import Comment, PullRequest, Review
from src.github import logic as github_logic


def task_url_from_task_id(task_id: str) -> str:
    """
    Transforms an Asana Task's object-id into an url referring to the task in the Asana app
    """
    if task_id is None or not task_id:
        raise ValueError("task_url_from_task_id requires a task_id")
    return f"https://app.asana.com/0/0/{task_id}"


def extract_task_fields_from_pull_request(pull_request: PullRequest) -> dict:
    """
    Extracts and transforms all relevant fields of a GitHub PullRequest into their corresponding
    equivalent fields, as relevant to an Asana Task
    :return: Returns the following fields: assignee, name, html_notes and followers
    """
    if pull_request is None:
        raise ValueError("extract_task_fields_from_pull_request requires a pull_request")
    return {
        "assignee": _task_assignee_from_pull_request(pull_request),
        "name": _task_name_from_pull_request(pull_request),
        "html_notes": _task_description_from_pull_request(pull_request),
        "completed": _task_completion_from_pull_request(pull_request),
        "followers": _task_followers_from_pull_request(pull_request),
    }


def _task_assignee_from_pull_request(pull_request: PullRequest) -> Optional[str]:
    assignee_handle = pull_request.assignee()
    return _asana_user_id_from_github_handle(assignee_handle)


def _asana_user_id_from_github_handle(github_handle: str) -> Optional[str]:
    return dynamodb_client.get_asana_domain_user_id_from_github_handle(github_handle)


def _asana_display_name_for_github_user(github_user: dict) -> str:
    """
        Retrieves a display name for a GitHub user that is usable in Asana. If the GitHub user is known by SGTM to
        be an Asana user, then an Asana user URL will be returned, otherwise the display name will be of the form:
                GitHub user 'David Brandt (padresmurfa)'
            or  Github user 'padresmurfa'
    """
    if github_user is None or "login" not in github_user or not github_user["login"].strip():
        raise ValueError("_asana_display_name_for_github_user requires a github_user with a 'login' value")
    github_user_handle = github_user.get("login")
    if github_user_handle is not None:
        asana_author_user = _asana_user_url_from_github_user_handle(github_user_handle)
        if asana_author_user is not None:
            return asana_author_user
    # default to returning GitHub user details, if Asana user details are not available
    github_user_name = github_user.get("name", None)
    if github_user_name is not None and github_user_name.strip():
        return f"GitHub user '{github_user_name} ({github_user_handle})'"
    return f"GitHub user '{github_user_handle}'"


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
            return _asana_user_url_from_github_user_handle(github_handle)

    return re.sub(github_logic.GITHUB_MENTION_REGEX, _github_mention_to_asana_mention, text)


def asana_comment_from_github_comment(comment: Comment) -> str:
    """
    Extracts the GitHub author and comment text from a GitHub Comment, and transforms them into
    a suitable html comment string for Asana. This will involve looking up the GitHub author in
    DynamoDb to determine the Asana userid.
    """
    if comment is None:
        raise ValueError("asana_comment_from_github_comment requires a comment")
    github_author = comment.author()
    display_name = _asana_display_name_for_github_user(github_author)
    comment_text = _transform_github_mentions_to_asana_mentions(escape(comment.body(), quote=False))
    return _wrap_in_tag("body")(
        _wrap_in_tag("strong")(f"{display_name} commented:\n") + comment_text
    )


# https://developer.github.com/v4/reference/enum/pullrequestreviewstate/
_review_action_to_text_map = {
    "APPROVED": "approved",
    "CHANGES_REQUESTED": "requested changes",
    "COMMENTED": "reviewed",
    "DISMISSED": "reviewed",
}


def asana_comment_from_github_review(review: Review) -> str:
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

    if not review_body and inline_comments:
        return _wrap_in_tag("body")(
            _wrap_in_tag("strong")(
                f"{user_display_name} left inline comments:\n" + "\n\n".join(inline_comments)
            )
        )

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
    github_author_handle = pull_request.author_handle()
    author = _asana_user_url_from_github_user_handle(github_author_handle)
    if author is None:
        github_author = pull_request.author()
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
    asana_domain_user_ids = [
        _asana_user_id_from_github_handle(gh_handle)
        for gh_handle in github_logic.all_pull_request_participants(pull_request)
    ]
    return [
        asana_domain_user_id
        for asana_domain_user_id in asana_domain_user_ids
        if asana_domain_user_id is not None
    ]


def _wrap_in_tag(tag_name: str) -> Callable[[str], str]:
    def inner(text: str) -> str:
        return f"<{tag_name}>{text}</{tag_name}>"

    return inner
