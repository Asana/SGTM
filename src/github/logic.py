import re
from typing import List
from src.logger import logger

from . import client as github_client
from src.github.models import Comment, PullRequest, MergeableState, Review
from enum import Enum, unique
from src.github.helpers import pull_request_has_label
from src.config import (
    SGTM_FEATURE__AUTOMERGE_ENABLED,
    SGTM_FEATURE__DISABLE_GITHUB_TEAM_SUBSCRIPTION,
    SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS,
)

GITHUB_MENTION_REGEX = "\B@([a-zA-Z0-9_\-]+)"
GITHUB_ATTACHMENT_REGEX = "!\[(.*?)\]\((.+?(\.png|\.jpg|\.jpeg|\.gif))"

AUTOMERGE_COMMENT_WARNING_AFTER_TESTS_AND_APPROVAL = (
    "**:warning: Reviewer:** If you approve this PR, it will be auto-merged as soon as"
    " tests pass. If you don't want this to be auto-merged, either Request Changes or"
    " remove the auto-merge label before accepting."
)

AUTOMERGE_COMMENT_WARNING_AFTER_APPROVAL = (
    "**:warning: Reviewer:** If you approve this PR, it will be auto-merged immediately."
    " If you don't want this to be auto-merged, either Request Changes or"
    " remove the auto-merge label before accepting."
)


@unique
class AutomergeLabel(Enum):
    AFTER_TESTS_AND_APPROVAL = "merge after tests and approval"
    AFTER_TESTS = "merge after tests"
    AFTER_APPROVAL = "merge after approval"
    IMMEDIATELY = "merge immediately"


@unique
class ApprovedBeforeMergeStatus(Enum):
    NO = 0
    NEEDS_FOLLOWUP = 1
    APPROVED = 2


def inject_asana_task_into_pull_request_body(body: str, task_url: str) -> str:
    return body + "\n\n\n" + f"Pull Request synchronized with [Asana task]({task_url})"


def _extract_mentions(text: str) -> List[str]:
    return re.findall(GITHUB_MENTION_REGEX, text)


def _pull_request_body_mentions(pull_request: PullRequest) -> List[str]:
    return _extract_mentions(pull_request.body())


def comment_participants_and_mentions(comment: Comment) -> List[str]:
    return list(set([comment.author_handle()] + _extract_mentions(comment.body())))


def review_participants_and_mentions(review: Review) -> List[str]:
    review_texts = [review.body()] + [comment.body() for comment in review.comments()]
    return list(
        set(
            [review.author_handle()]
            + [
                mention
                for review_text in review_texts
                for mention in _extract_mentions(review_text)
            ]
        )
    )


def pull_request_approved_before_merging(
    pull_request: PullRequest,
) -> ApprovedBeforeMergeStatus:
    """
    The pull request has been approved if the last review (approval/changes
    requested) before merging was an approval, ignoring reviews from users that
    are marked as needing follow-up review.
    """
    assert pull_request.merged(), "Checked for pre-merge approval on a non-merged PR"
    merged_at = pull_request.merged_at()
    if merged_at is None:
        # The PR was merged but we don't know when.  Assume it was approved after.
        return ApprovedBeforeMergeStatus.NO

    premerge_reviews = sorted(
        (
            review
            for review in pull_request.reviews()
            if review.is_approval_or_changes_requested()
            and review.submitted_at() < merged_at
        ),
        key=lambda r: r.submitted_at(),
    )

    if len(premerge_reviews) == 0:
        # We didn't find any reviews
        return ApprovedBeforeMergeStatus.NO

    latest_review = premerge_reviews[-1]
    if not latest_review.is_approval():
        return ApprovedBeforeMergeStatus.NO

    # We know the last review was an approval, but we want to figure out
    # whether it still needs follow-up review.
    if latest_review.author().login() in SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS:
        # The last review needs follow-up - check if there was a review just
        # before that which doesn't need follow-up.
        no_followup_reviews = [
            r
            for r in premerge_reviews
            if r.author().login() not in SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS
        ]
        if len(no_followup_reviews) == 0 or not no_followup_reviews[-1].is_approval():
            # There were no approvals before this that didn't need follow-up review.
            return ApprovedBeforeMergeStatus.NEEDS_FOLLOWUP

    return ApprovedBeforeMergeStatus.APPROVED


def _is_approval_comment_body(body: str) -> bool:
    return (
        re.search(
            "sgtm|lgtm|sounds good|sound good|looks good|look good|looks great|look"
            " great|\+1|ship\s?it|👍|🚢",
            body.lower(),
        )
        is not None
    )


def pull_request_approved_after_merging(pull_request: PullRequest) -> bool:
    """
    If changes were requested, addressed, and then the PR merge, the state of the pr will still be
    "changes requested" unless the original review is dismissed and the reviewer is re-requested
    to review the pr. This is described here:
    https://stackoverflow.com/questions/40893008/how-to-resume-review-process-after-updating-pull-request-at-github

    To improve the UX of this process, we will still consider the pr approved if we find a comment on the pr with
    a marker text, such as "LGTM" or "looks good to me".

    This method handles this part of the logic.

    NOTE: We ignore actions from users who are marked as needing follow-up
    review, since their input isn't useful after a PR has been merged.
    """
    merged_at = pull_request.merged_at()
    if merged_at is not None:
        # the marker text may occur in any comment in the pr that occurred post-merge
        # TODO: consider whether we should allow pre-merge comments to have the same effect? It seems likely that
        #       this limitation is just intended to ensure that the asana task is not closed due to a marker text unless
        #       the PR has been merged into next-master, otherwise it might be forgotten in an approved state
        postmerge_comments = [
            comment
            for comment in pull_request.comments()
            if comment.published_at() >= merged_at
            and comment.author_handle() != pull_request.author_handle()
            and comment.author().login()
            not in SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS
            # TODO: consider using the lastEditedAt timestamp. A reviewer might comment: "noice!" prior to the PR being
            #       merged, then update their comment to "noice! LGTM!!!" after it had been merged.  This would however not
            #       suffice to cause the PR to be considered approved after merging.
        ]
        # or it may occur in the summary text of a review that was submitted after the pr was merged
        postmerge_reviews = [
            review
            for review in pull_request.reviews()
            if review.submitted_at() >= merged_at
            and review.author().login()
            not in SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS
        ]
        body_texts = [c.body() for c in postmerge_comments] + [
            r.body() for r in postmerge_reviews
        ]
        return bool(
            [
                body_text
                for body_text in body_texts
                if _is_approval_comment_body(body_text)
            ]
        )
    return False


def pull_request_participants(pull_request: PullRequest) -> List[str]:
    return list(
        set(
            gh_handle
            for gh_handle in (
                [pull_request.author_handle()]
                + pull_request.assignees()
                + pull_request.requested_reviewers(include_team_members=not SGTM_FEATURE__DISABLE_GITHUB_TEAM_SUBSCRIPTION)
                + _pull_request_body_mentions(pull_request)
            )
            if gh_handle
        )
    )


def maybe_add_automerge_warning_comment(pull_request: PullRequest):
    """Adds comment warnings if automerge label is enabled"""

    if SGTM_FEATURE__AUTOMERGE_ENABLED:
        owner = pull_request.repository_owner_handle()
        repo_name = pull_request.repository_name()
        pr_number = pull_request.number()

        has_automerge_after_tests_and_approval = pull_request_has_label(
            pull_request, AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
        )
        has_automerge_after_approval = pull_request_has_label(
            pull_request, AutomergeLabel.AFTER_APPROVAL.value
        )
        automerge_comment = (
            AUTOMERGE_COMMENT_WARNING_AFTER_TESTS_AND_APPROVAL
            if has_automerge_after_tests_and_approval
            else AUTOMERGE_COMMENT_WARNING_AFTER_APPROVAL
        )

        # if a PR has an automerge label and doesn't contain a comment warning, we want to maybe add a warning comment
        # only add warning comment if it's set to auto-merge after approval and hasn't yet been approved to limit noise

        if (
            (has_automerge_after_tests_and_approval or has_automerge_after_approval)
            and not _pull_request_has_automerge_comment(pull_request, automerge_comment)
            and not pull_request.is_approved()
        ):

            github_client.add_pr_comment(owner, repo_name, pr_number, automerge_comment)


# returns True if the pull request was automerged, False if not
def maybe_automerge_pull_request(pull_request: PullRequest) -> bool:
    if _is_pull_request_ready_for_automerge(pull_request):
        logger.info(
            f"Pull request {pull_request.id()} is able to be automerged,"
            " automerging now"
        )
        github_client.merge_pull_request(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            pull_request.number(),
            pull_request.title(),
            pull_request.body(),
        )
        return True
    else:
        return False


# ----------------------------------------------------------------------------------
# Automerge helpers
# ----------------------------------------------------------------------------------


def _is_pull_request_ready_for_automerge(pull_request: PullRequest) -> bool:
    # autofail if not enabled or pull request isn't open
    if (
        not SGTM_FEATURE__AUTOMERGE_ENABLED
        or pull_request.closed()
        or pull_request.merged()
    ):
        return False

    # if there are multiple labels, we use the most permissive to define automerge behavior
    if pull_request_has_label(pull_request, AutomergeLabel.IMMEDIATELY.value):
        return pull_request.mergeable() in (
            MergeableState.MERGEABLE,
            MergeableState.UNKNOWN,
        )

    if pull_request_has_label(pull_request, AutomergeLabel.AFTER_TESTS.value):
        return pull_request.is_build_successful() and pull_request.is_mergeable()

    if pull_request_has_label(
        pull_request, AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
    ):
        return (
            pull_request.is_build_successful()
            and pull_request.is_mergeable()
            and pull_request.is_approved()
        )

    if pull_request_has_label(pull_request, AutomergeLabel.AFTER_APPROVAL.value):
        return pull_request.is_mergeable() and pull_request.is_approved()

    return False


def _pull_request_has_automerge_comment(
    pull_request: PullRequest, automerge_comment: str
) -> bool:
    return any(
        comment.body() == automerge_comment for comment in pull_request.comments()
    )
