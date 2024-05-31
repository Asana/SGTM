import re
from html import escape
from datetime import datetime, timedelta
from typing import Callable, Match, Optional, List, Dict, Set
from src.dynamodb import client as dynamodb_client
from src.asana import logic as asana_logic
from src.config import GITHUB_USERNAMES_TO_ASANA_GIDS_S3_PATH
from src.github.models import (
    Comment,
    PullRequest,
    Review,
    ReviewState,
    User,
    Assignee,
    AssigneeReason,
)
from src.asana import client as asana_client
from src.github import logic as github_logic
from src.logger import logger
import collections
import urllib.request
from src.markdown_parser import convert_github_markdown_to_asana_xml

AttachmentData = collections.namedtuple(
    "AttachmentData", "file_name file_url image_type"
)

StatusReason = collections.namedtuple("StatusReason", "is_complete reason")


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
        "completed": _task_completion_from_pull_request(pull_request).is_complete,
        "custom_fields": _custom_fields_from_pull_request(pull_request),
    }


def today_str() -> str:
    today = datetime.now()
    return today.strftime("%Y-%m-%d")


def default_due_date_str(reference_datetime: Optional[datetime] = None) -> str:
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
    if pull_request.closed():
        return "Merged" if pull_request.merged() else "Closed"
    else:
        return "Draft" if pull_request.is_draft() else "Open"


def _review_status_from_pull_request(pull_request: PullRequest) -> Optional[str]:
    if pull_request.is_draft():
        return "Not Ready"
    elif pull_request.is_needs_review():
        return "Needs Review"
    elif pull_request.is_approved():
        return "Approved"
    else:
        return "Changes Requested"


def _build_status_from_pull_request(pull_request: PullRequest) -> Optional[str]:
    build_status = pull_request.build_status()
    return build_status.capitalize() if build_status is not None else None


def _author_asana_user_id_from_pull_request(pull_request: PullRequest) -> Optional[str]:
    return dynamodb_client.get_asana_domain_user_id_from_github_handle(
        pull_request.author_handle()
    )


_custom_fields_to_extract_map = {
    "PR Status": _task_status_from_pull_request,
    "Build": _build_status_from_pull_request,
    "Author (SGTM)": _author_asana_user_id_from_pull_request,
    "Review Status": _review_status_from_pull_request,
}


def _custom_fields_from_pull_request(pull_request: PullRequest) -> Dict:
    """
    We currently expect the project to have three custom fields with its corresponding enum options:
        • PR Status: "Open", "Draft", "Closed", "Merged"
        • Build: "Success", "Failure"
        • Review Status: "Needs Review", "Changes Requested", "Approved", "Not Ready"
    """
    repository_id = pull_request.repository_id()
    project_id = dynamodb_client.get_asana_id_from_github_node_id(repository_id)

    if project_id is None:
        logger.error(
            f"Task not found for pull request {pull_request.id()}."
        )
        return {}
    else:
        custom_field_map = {
            cf["custom_field"]["name"]: cf["custom_field"]
            for cf in asana_client.get_project_custom_fields(project_id)
        }
        data = {}
        for custom_field_name, action in _custom_fields_to_extract_map.items():
            if custom_field_name not in custom_field_map:
                continue

            custom_field = custom_field_map[custom_field_name]
            value_name = action(pull_request)

            if value_name:
                custom_field_id = custom_field["gid"]
                custom_field_value = _get_custom_field_value(custom_field, value_name)
                if custom_field_value:
                    data[custom_field_id] = custom_field_value

        return data


def _get_custom_field_value(custom_field: dict, value_name: str) -> Optional[str]:
    if custom_field["resource_subtype"] == "enum":
        enum_options = custom_field["enum_options"]
        filtered_gid = [
            enum_option["gid"]
            for enum_option in enum_options
            if enum_option["name"] == value_name and enum_option["enabled"]
        ]
        return filtered_gid[0] if filtered_gid else None
    else:
        return value_name


def _task_assignee_from_pull_request(pull_request: PullRequest) -> Optional[str]:
    if asana_logic.should_set_task_owner_to_pr_author(pull_request):
        return _author_asana_user_id_from_pull_request(pull_request)
    assignee = pull_request.assignee()
    return dynamodb_client.get_asana_domain_user_id_from_github_handle(assignee.login)


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
    user_id = dynamodb_client.get_asana_domain_user_id_from_github_handle(github_handle)
    if user_id is None:
        return None
    return _wrap_in_tag(
        "A",
        attrs={
            "data-asana-gid": user_id,
            "href": f"https://github.com/{github_handle}",
        },
    )(github_handle)


def _task_name_from_pull_request(pull_request: PullRequest) -> str:
    return "#{} - {}".format(pull_request.number(), pull_request.title())


def _transform_github_mentions_to_asana_mentions(text: str) -> str:
    def _github_mention_to_asana_mention(match: Match[str]) -> str:
        github_handle = match.group(1)
        asana_user_id = dynamodb_client.get_asana_domain_user_id_from_github_handle(
            github_handle
        )
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
    comment_text = _format_github_text_for_asana(comment.body())
    return _wrap_in_tag("body")(
        display_name
        + " "
        + _wrap_in_tag("A", attrs={"href": comment.url()})("commented:")
        + "\n"
        + comment_text
    )


_image_extension_to_type = {
    ".png": "image/png",
    ".jpg": "image/jpg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
}


def _extract_attachments(body_text: str) -> List[AttachmentData]:
    """
    Finds, but does not replace, all the image attachment URLS (those that end in png, gif,
    jpg, or jpeg) in the body_text.
    """
    attachments = []
    matches = re.findall(github_logic.GITHUB_ATTACHMENT_REGEX, body_text)
    for img_name, img_url, img_ext in matches:
        image_type = _image_extension_to_type.get(img_ext)

        # Asana API accepts multiple attachments with same name, so defaulting to "github_attachment" is valid
        full_name = img_name if img_name else "github_attachment"
        if image_type and img_ext not in full_name:
            full_name += img_ext
        attachments.append(
            AttachmentData(file_name=full_name, file_url=img_url, image_type=image_type)
        )
    return attachments


def create_attachments(body_text: str, task_id: str) -> None:
    attachments = _extract_attachments(body_text)
    for attachment in attachments:
        try:
            with urllib.request.urlopen(attachment.file_url) as f:
                attachment_contents = f.read()
                asana_client.create_attachment_on_task(
                    task_id,
                    attachment_contents,
                    attachment.file_name,
                    attachment.image_type,
                )
        except Exception:
            logger.warning("Attachment creation failed. Creating task comment anyway.")


_review_action_to_text_map: Dict[ReviewState, str] = {
    ReviewState.APPROVED: "approved",
    ReviewState.CHANGES_REQUESTED: "requested changes",
    ReviewState.COMMENTED: "reviewed",
    ReviewState.DISMISSED: "reviewed",
}


def get_linked_task_ids(pull_request: PullRequest) -> Set[str]:
    """
    Extracts linked task ids from the body of the PR.
    We expect linked tasks to be in the description in a line under the line containing "Asana tasks:".

    :return: Returns a list of task ids.
    """
    body_lines = pull_request.body().splitlines()
    curr_line = 0
    task_ids = set()
    seen_asana_tasks_line = False

    while curr_line < len(body_lines):
        stripped_line = body_lines[curr_line].strip()
        if stripped_line.startswith("Asana tasks:"):
            seen_asana_tasks_line = True
            curr_line += 1
        elif seen_asana_tasks_line:
            task_urls = stripped_line.split()
            line_has_task_urls = False
            for url in task_urls:
                maybe_id = re.search("\d+(?!.*\d)", url)
                if maybe_id is not None:
                    line_has_task_urls = True
                    task_ids.add(maybe_id.group())

            if line_has_task_urls:
                curr_line += 1
            else:
                # no more task urls if the last one is not defined
                break
        else:
            curr_line += 1

    return task_ids


def asana_comment_from_github_review(review: Review) -> str:
    """
    Extracts the GitHub author and comments from a GitHub Review, and transforms them into
    a suitable html comment string for Asana. This will involve looking up the GitHub author in
    DynamoDb to determine the Asana domain user id of the review author and any @mentioned GitHub
    users.
    """
    user_display_name = _asana_display_name_for_github_user(review.author())

    if review.is_just_comments():
        # When a user replies to an inline comment,
        # or writes inline comments without a review,
        # github still creates a Review object,
        # even though nothing in github looks like a review
        # If that's the case, there is no meaningful review state ("commented" isn't helpful)
        # and the link to it will either not point anywhere, or be less useful than the individual links on each comment.
        review_action = _wrap_in_tag("strong")("left inline comments:\n")
    else:
        review_action = _wrap_in_tag("A", attrs={"href": review.url()})(
            _review_action_to_text_map.get(review.state(), "commented")
        )

    review_body = _format_github_text_for_asana(review.body())
    if review_body:
        header = (
            _wrap_in_tag("strong")(f"{user_display_name} {review_action} :\n")
            + review_body
        )
    else:
        header = _wrap_in_tag("strong")(f"{user_display_name} {review_action}")

    # For each comment, prefix its text with a bracketed number that is a link to the Github comment.
    inline_comments = [
        _wrap_in_tag("A", attrs={"href": comment.url()})(f"[{i}] ")
        + _format_github_text_for_asana(comment.body())
        for i, comment in enumerate(review.comments(), start=1)
    ]
    if inline_comments:
        comments_html = "\n".join(inline_comments)
        if not review.is_just_comments():
            # If this was an inline reply, we already added "and left inline comments" above.
            comments_html = (
                _wrap_in_tag("strong")("\n\nand left inline comments:\n")
                + comments_html
            )
    else:
        comments_html = ""

    return _wrap_in_tag("body")(header + comments_html)


def _format_github_text_for_asana(text: str) -> str:
    return _transform_github_mentions_to_asana_mentions(
        convert_github_markdown_to_asana_xml(text)
    )


def _generate_assignee_description(assignee: Assignee) -> str:
    assignee_asana_user = _asana_user_url_from_github_user_handle(assignee.login)
    if assignee_asana_user is None:
        assignee_asana_user = f"GitHub user '{assignee.login}'"

    if assignee.reason == AssigneeReason.NO_ASSIGNEE:
        return (
            f"\nAssigned to self, {assignee_asana_user}, because no assignees were"
            " selected."
        )
    elif assignee.reason == AssigneeReason.MULTIPLE_ASSIGNEES:
        return (
            f"\nAssigned to {assignee_asana_user}, first assignee alphabetically from"
            " assignees provided."
        )
    else:
        # Single assignee, no changes from Pull Request
        return ""


def _task_description_from_pull_request(pull_request: PullRequest) -> str:
    link_to_pr = _link(pull_request.url())
    github_author = pull_request.author()
    author = _asana_user_url_from_github_user_handle(github_author.login())
    if author is None:
        author = _asana_display_name_for_github_user(github_author)
    status_reason = _task_completion_from_pull_request(pull_request)
    status = "complete" if status_reason.is_complete else "incomplete"
    return _wrap_in_tag("body")(
        _wrap_in_tag("em")(
            "This is a one-way sync from GitHub to Asana. Do not edit this task or"
            " comment on it!"
        )
        + f"\n\n\uD83D\uDD17 {link_to_pr}"
        + "\n✍️ "
        + author
        + _generate_assignee_description(pull_request.assignee())
        + f"\n❗️Task is {status} because {status_reason.reason}"
        + _wrap_in_tag("strong")("\n\nDescription:\n")
        + _format_github_text_for_asana(pull_request.body())
    )


def _task_completion_from_pull_request(pull_request: PullRequest) -> StatusReason:
    if not pull_request.closed():
        return StatusReason(False, "the pull request is open.")
    elif not pull_request.merged():
        return StatusReason(True, "the pull request was closed without merging code.")

    approved_before_merge = github_logic.pull_request_approved_before_merging(
        pull_request
    )
    if approved_before_merge == github_logic.ApprovedBeforeMergeStatus.APPROVED:
        return StatusReason(True, "the pull request was approved before merging.")
    elif github_logic.pull_request_approved_after_merging(pull_request):
        return StatusReason(True, "the pull request was approved after merging.")
    elif approved_before_merge == github_logic.ApprovedBeforeMergeStatus.NEEDS_FOLLOWUP:
        return StatusReason(
            False,
            "the pull request was approved before merging by a Github user that "
            + "requires follow-up review.  The Reviewer can close this task by "
            + 'commenting "LGTM" on the Pull Request.',
        )
    else:
        return StatusReason(
            False,
            "the pull request hasn't yet been approved by a reviewer after merging. "
            + 'The reviewer can close this task by commenting "LGTM" on the Pull'
            " Request.",
        )


def task_followers_from_comment(comment: Comment) -> List[str]:
    return _task_followers_from_gh_handles(
        github_logic.comment_participants_and_mentions(comment)
    )


def task_followers_from_review(review: Review) -> List[str]:
    return _task_followers_from_gh_handles(
        github_logic.review_participants_and_mentions(review)
    )


def task_followers_from_pull_request(pull_request: PullRequest) -> List[str]:
    return _task_followers_from_gh_handles(
        github_logic.pull_request_participants(pull_request)
    )


def _task_followers_from_gh_handles(gh_handles: List[str]) -> List[str]:
    followers = [
        asana_user_id
        for github_handle in gh_handles
        if (
            asana_user_id := dynamodb_client.get_asana_domain_user_id_from_github_handle(
                github_handle
            )
        )
        is not None
    ]
    if len(followers) == 0:
        logger.warning(
            f"No asana followers found for github users {gh_handles}. This list likely includes bots or users that are not in your {GITHUB_USERNAMES_TO_ASANA_GIDS_S3_PATH}. Consider adding them to silence this warning."
        )
    return followers


def _wrap_in_tag(
    tag_name: str, attrs: Optional[Dict[str, str]] = None
) -> Callable[[str], str]:
    if attrs is not None:
        # This will always start with a blank space, so that it's separate from the tag name.
        attr_list = "".join(f' {k}="{escape(v)}"' for k, v in attrs.items())
    else:
        attr_list = ""

    def inner(text: str) -> str:
        return f"<{tag_name}{attr_list}>{text}</{tag_name}>"

    return inner


def _link(url: str) -> str:
    return _wrap_in_tag("A", {"href": url})(url)
