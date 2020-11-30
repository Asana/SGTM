import re
import os
from typing import List
from src.logger import logger
from . import client as github_client
from src.github.models import PullRequest, MergeableState
from enum import Enum, unique

GITHUB_MENTION_REGEX = "\B@([a-zA-Z0-9_\-]+)"
GITHUB_ATTACHMENT_REGEX = "!\[(.*?)\]\((.+?(\.png|\.jpg|\.jpeg|\.gif))"

AUTOMERGE_TITLE_WARNING = " <auto-merge>"
AUTOMERGE_COMMENT_WARNING = "**:warning: Reviewer:** If you approve this PR, it will be auto-merged as soon as tests pass. If you don't want this to be auto-merged, either Request Changes or remove the auto-merge label before accepting."


@unique
class AutomergeLabel(Enum):
    AFTER_TESTS_AND_APPROVAL = "merge after tests and approval"
    AFTER_TESTS = "merge after tests"
    IMMEDIATELY = "merge immediately"


def inject_asana_task_into_pull_request_body(body: str, task_url: str) -> str:
    return body + "\n\n\n" + f"Pull Request synchronized with [Asana task]({task_url})"


def _extract_mentions(text: str) -> List[str]:
    return re.findall(GITHUB_MENTION_REGEX, text)


def _pull_request_comment_mentions(pull_request: PullRequest) -> List[str]:
    comment_texts = [comment.body() for comment in pull_request.comments()]
    return [
        mention
        for comment_text in comment_texts
        for mention in _extract_mentions(comment_text)
    ]


def _pull_request_review_mentions(pull_request: PullRequest) -> List[str]:
    review_texts = [review.body() for review in pull_request.reviews()] + [
        comment.body()
        for comments in [review.comments() for review in pull_request.reviews()]
        for comment in comments
    ]
    return [
        mention
        for review_text in review_texts
        for mention in _extract_mentions(review_text)
    ]


def _pull_request_body_mentions(pull_request: PullRequest) -> List[str]:
    return _extract_mentions(pull_request.body())


def _pull_request_commenters(pull_request: PullRequest) -> List[str]:
    return sorted(comment.author_handle() for comment in pull_request.comments())


def pull_request_approved_before_merging(pull_request: PullRequest) -> bool:
    """
    The pull request has been approved if the last review (approval/changes
    requested) before merging was an approval
    """
    merged_at = pull_request.merged_at()
    if merged_at is not None:
        premerge_reviews = [
            review
            for review in pull_request.reviews()
            if review.is_approval_or_changes_requested()
            and review.submitted_at() < merged_at
        ]
        if premerge_reviews:
            latest_review = sorted(premerge_reviews, key=lambda r: r.submitted_at())[-1]
            return latest_review.is_approval()
    return False


def _is_approval_comment_body(body: str) -> bool:
    return (
        re.search(
            "sgtm|lgtm|sounds good|sound good|looks good|look good|looks great|look great|\+1|ship\s?it|👍|🚢",
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
            # TODO: consider using the lastEditedAt timestamp. A reviewer might comment: "noice!" prior to the PR being
            #       merged, then update their comment to "noice! LGTM!!!" after it had been merged.  This would however not
            #       suffice to cause the PR to be considered approved after merging.
        ]
        # or it may occur in the summary text of a review that was submitted after the pr was merged
        postmerge_reviews = [
            review
            for review in pull_request.reviews()
            if review.submitted_at() >= merged_at
        ]
        body_texts = [c.body() for c in postmerge_comments] + [
            r.body() for r in postmerge_reviews
        ]
        # TODO: consider whether we should disallow the pr author to approve their own pr via a LGTM comment
        return bool(
            [
                body_text
                for body_text in body_texts
                if _is_approval_comment_body(body_text)
            ]
        )
    return False


def all_pull_request_participants(pull_request: PullRequest) -> List[str]:
    return list(
        set(
            gh_handle
            for gh_handle in (
                [pull_request.author_handle()]
                + pull_request.assignees()
                + pull_request.reviewers()
                + pull_request.requested_reviewers()
                + _pull_request_commenters(pull_request)
                + _pull_request_comment_mentions(pull_request)
                + _pull_request_review_mentions(pull_request)
                + _pull_request_body_mentions(pull_request)
            )
            if gh_handle
        )
    )


def maybe_add_automerge_warning_title_and_comment(pull_request: PullRequest):
    """Adds title and comment warnings if automerge label is enabled"""

    if _is_automerge_feature_enabled():
        owner = pull_request.repository_owner_handle()
        repo_name = pull_request.repository_name()
        pr_number = pull_request.number()

        # if a PR has an automerge label and its title doesn't contain a warning, we want to add a warning
        # to the title and maybe add a warning comment
        if _pull_request_has_automerge_label(
            pull_request
        ) and not _pull_request_has_automerge_title(pull_request):
            new_title = pull_request.title() + AUTOMERGE_TITLE_WARNING
            github_client.edit_pr_title(owner, repo_name, pr_number, new_title)
            pull_request.set_title(new_title)

            # only add warning comment if it's set to auto-merge after approval and hasn't yet been approved to limit noise
            # this will lead to multiple warning comments on the same PR if labels are added and removed multiple times
            if (
                _pull_request_has_label(
                    pull_request, AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
                and not pull_request.is_approved()
            ):
                github_client.add_pr_comment(
                    owner, repo_name, pr_number, AUTOMERGE_COMMENT_WARNING
                )

        # remove automerge warning in title if PR doesn't have label anymore
        elif not _pull_request_has_automerge_label(
            pull_request
        ) and _pull_request_has_automerge_title(pull_request):
            new_title = pull_request.title().replace(AUTOMERGE_TITLE_WARNING, "")
            github_client.edit_pr_title(owner, repo_name, pr_number, new_title)
            pull_request.set_title(new_title)


# returns True if the pull request was automerged, False if not
def maybe_automerge_pull_request(pull_request: PullRequest) -> bool:
    if _is_pull_request_ready_for_automerge(pull_request):
        logger.info(
            f"Pull request {pull_request.id()} is able to be automerged, automerging now"
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
    automerge_enabled = _is_automerge_feature_enabled()

    # autofail if not enabled or pull request isn't open
    if not automerge_enabled or pull_request.closed() or pull_request.merged():
        return False

    # if there are multiple labels, we use the most permissive to define automerge behavior
    if _pull_request_has_label(pull_request, AutomergeLabel.IMMEDIATELY.value):
        return pull_request.mergeable() in (
            MergeableState.MERGEABLE,
            MergeableState.UNKNOWN,
        )

    if _pull_request_has_label(pull_request, AutomergeLabel.AFTER_TESTS.value):
        return pull_request.is_build_successful() and pull_request.is_mergeable()

    if _pull_request_has_label(
        pull_request, AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
    ):
        return (
            pull_request.is_build_successful()
            and pull_request.is_mergeable()
            and pull_request.is_approved()
        )

    return False


def _is_automerge_feature_enabled():
    return os.getenv("SGTM_FEATURE__AUTOMERGE_ENABLED") == "true"


def _pull_request_has_automerge_label(pull_request: PullRequest) -> bool:
    return any(
        map(
            lambda label: _pull_request_has_label(pull_request, label.value),
            AutomergeLabel,
        )
    )


def _pull_request_has_label(pull_request: PullRequest, label: str) -> bool:
    label_names = map(lambda label: label.name(), pull_request.labels())
    return label in label_names


def _pull_request_has_automerge_title(pull_request: PullRequest) -> bool:
    return AUTOMERGE_TITLE_WARNING in pull_request.title()
