import re
from typing import List
from datetime import datetime
from src.logger import logger
from src.github.models import PullRequest

GITHUB_MENTION_REGEX = "\B@([a-zA-Z0-9_\-]+)"


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
            "lgtm|looks good|look good|looks great|look great|\+1|ship\s?it|👍|🚢",
            body.lower(),
        )
        is not None
    )


def pull_request_approved_after_merging(pull_request: PullRequest) -> bool:
    merged_at = pull_request.merged_at()
    postmerge_comments = [
        comment
        for comment in pull_request.comments()
        if comment.published_at() > merged_at
    ]
    postmerge_reviews = [
        review for review in pull_request.reviews() if review.submitted_at() > merged_at
    ]
    body_texts = [c.body() for c in postmerge_comments] + [
        r.body() for r in postmerge_reviews
    ]
    return bool(
        [body_text for body_text in body_texts if _is_approval_comment_body(body_text)]
    )


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
