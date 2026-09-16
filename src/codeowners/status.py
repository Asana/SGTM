"""Decide whether a pull request's codeowner requirements are satisfied.

Semantics (agreed in the feature design):

* A file is *approved* when the latest approve / request-changes / dismissed
  review by any owner of that file (its whole owner set, never the PR author)
  is an approval. It has *changes requested* when that latest review asks for
  changes, is *stale* when that latest review was dismissed (a push dismissed
  the approval), and is *needed* otherwise.
* A requirement's status is the worst of its files: Changes Requested, then
  Needed, then Approval Stale, then Approved. A requirement without files is
  No Longer Required. A requirement still unapproved when the PR merges is
  Merged with Bypass.
* The PR task's aggregate: Not Required (no codeowned files), Not Yet
  Requested (codeowned files but the label was never added), Pending,
  Partially Approved, Approved, or Changes Requested.
* The *primary review* is an approval from someone who is not a codeowner on
  this PR, or from a codeowner the author chose (asked to review, or set as
  GitHub assignee). Codeowners requested only by SGTM or by GitHub's
  CODEOWNERS auto-request count toward the codeowner side alone.
"""
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set

from src.config import SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS
from src.github.models import PullRequest, Review, ReviewState

from .requirements import CodeownerRequirement, OwnerSet

# Expands an owner set (teams and individuals) into the GitHub logins that may
# act for it. Supplied by the caller, which knows how to look up team members.
PoolResolver = Callable[[OwnerSet], Set[str]]

DECISIVE_STATES = (
    ReviewState.APPROVED,
    ReviewState.CHANGES_REQUESTED,
    ReviewState.DISMISSED,
)


@unique
class RequirementStatus(Enum):
    """Values of the subtask's "Codeowner Approval (SGTM)" custom field."""

    NEEDED = "Needed"
    APPROVED = "Approved"
    APPROVAL_STALE = "Approval Stale"
    CHANGES_REQUESTED = "Changes Requested"
    NO_LONGER_REQUIRED = "No Longer Required"
    MERGED_WITH_BYPASS = "Merged with Bypass"


@unique
class FileStatus(Enum):
    NEEDED = "needed"
    APPROVED = "approved"
    STALE = "stale"
    CHANGES_REQUESTED = "changes_requested"


@unique
class ParentCodeownerStatus(Enum):
    """Values of the PR task's "Codeowner Review (SGTM)" custom field."""

    NOT_REQUIRED = "Not Required"
    NOT_YET_REQUESTED = "Not Yet Requested"
    PENDING = "Pending"
    PARTIALLY_APPROVED = "Partially Approved"
    APPROVED = "Approved"
    CHANGES_REQUESTED = "Changes Requested"


REVIEW_STATUS_NEEDS_CODEOWNER_APPROVAL = "Needs Codeowner Approval"


@dataclass
class FileEvaluation:
    path: str
    owners: OwnerSet
    status: FileStatus
    # The review that decided the status, when one exists.
    review: Optional[Review] = None

    def reviewer(self) -> Optional[str]:
        return self.review.author_handle() if self.review is not None else None


@dataclass
class RequirementEvaluation:
    requirement: CodeownerRequirement
    status: RequirementStatus
    files: List[FileEvaluation] = field(default_factory=list)

    @property
    def owner_set(self) -> OwnerSet:
        return self.requirement.owner_set

    def is_satisfied(self) -> bool:
        return self.status in (
            RequirementStatus.APPROVED,
            RequirementStatus.NO_LONGER_REQUIRED,
        )

    def is_outstanding(self) -> bool:
        return self.status in (
            RequirementStatus.NEEDED,
            RequirementStatus.APPROVAL_STALE,
            RequirementStatus.CHANGES_REQUESTED,
        )

    def _latest_file_review(self, status: FileStatus) -> Optional[Review]:
        reviews = [f.review for f in self.files if f.status is status and f.review]
        if not reviews:
            return None
        return max(reviews, key=lambda r: r.submitted_at())

    def approval_review(self) -> Optional[Review]:
        """The most recent approval that satisfied a file, if the whole
        requirement is approved."""
        if self.status is not RequirementStatus.APPROVED:
            return None
        return self._latest_file_review(FileStatus.APPROVED)

    def changes_requested_review(self) -> Optional[Review]:
        return self._latest_file_review(FileStatus.CHANGES_REQUESTED)

    def stale_review(self) -> Optional[Review]:
        return self._latest_file_review(FileStatus.STALE)


def latest_decisive_review(
    reviews: Iterable[Review], logins: Set[str]
) -> Optional[Review]:
    """The newest approve / changes-requested / dismissed review by any of `logins`."""
    relevant = [
        review
        for review in reviews
        if review.author_handle() in logins and review.state() in DECISIVE_STATES
    ]
    if not relevant:
        return None
    return max(relevant, key=lambda r: r.submitted_at())


def _file_status(review: Optional[Review]) -> FileStatus:
    if review is None:
        return FileStatus.NEEDED
    if review.state() is ReviewState.CHANGES_REQUESTED:
        return FileStatus.CHANGES_REQUESTED
    if review.state() is ReviewState.APPROVED:
        return FileStatus.APPROVED
    return FileStatus.STALE


def evaluate_requirement(
    requirement: CodeownerRequirement,
    resolve_pool: PoolResolver,
    reviews: Sequence[Review],
    author: str,
    merged: bool = False,
) -> RequirementEvaluation:
    """Evaluate one requirement against the pull request's reviews."""
    if not requirement.all_files():
        return RequirementEvaluation(requirement, RequirementStatus.NO_LONGER_REQUIRED)

    file_evaluations: List[FileEvaluation] = []
    for path in requirement.all_files():
        owners = requirement.owners_for_file(path)
        pool = resolve_pool(owners) - {author}
        review = latest_decisive_review(reviews, pool)
        file_evaluations.append(
            FileEvaluation(path, owners, _file_status(review), review)
        )

    statuses = {f.status for f in file_evaluations}
    if FileStatus.CHANGES_REQUESTED in statuses:
        status = RequirementStatus.CHANGES_REQUESTED
    elif FileStatus.NEEDED in statuses:
        status = RequirementStatus.NEEDED
    elif FileStatus.STALE in statuses:
        status = RequirementStatus.APPROVAL_STALE
    else:
        status = RequirementStatus.APPROVED

    if merged and status is not RequirementStatus.APPROVED:
        status = RequirementStatus.MERGED_WITH_BYPASS
    return RequirementEvaluation(requirement, status, file_evaluations)


def aggregate_parent_status(
    evaluations: Sequence[RequirementEvaluation],
    has_codeowned_files: bool,
    tasks_requested: bool,
) -> ParentCodeownerStatus:
    if not has_codeowned_files:
        return ParentCodeownerStatus.NOT_REQUIRED
    if not tasks_requested:
        return ParentCodeownerStatus.NOT_YET_REQUESTED
    active = [
        e for e in evaluations if e.status is not RequirementStatus.NO_LONGER_REQUIRED
    ]
    if not active:
        return ParentCodeownerStatus.NOT_REQUIRED
    if any(e.status is RequirementStatus.CHANGES_REQUESTED for e in active):
        return ParentCodeownerStatus.CHANGES_REQUESTED
    approved = [e for e in active if e.status is RequirementStatus.APPROVED]
    if len(approved) == len(active):
        return ParentCodeownerStatus.APPROVED
    if approved:
        return ParentCodeownerStatus.PARTIALLY_APPROVED
    return ParentCodeownerStatus.PENDING


@dataclass
class CodeownerSummary:
    """Everything the Asana side needs to know about a PR's codeowner state."""

    evaluations: List[RequirementEvaluation]
    codeowned_files: Dict[str, OwnerSet]
    tasks_requested: bool
    # Every login that may act as a codeowner on this PR (all pools together).
    codeowner_logins: Set[str]
    # Reviewers the author chose: people they asked to review, or set as the
    # GitHub assignee. Persisted by the controller because GitHub drops a
    # reviewer from `reviewRequests` once they review.
    human_chosen_logins: Set[str] = field(default_factory=set)

    def has_codeowned_files(self) -> bool:
        return bool(self.codeowned_files)

    def parent_status(self) -> ParentCodeownerStatus:
        return aggregate_parent_status(
            self.evaluations, self.has_codeowned_files(), self.tasks_requested
        )

    def outstanding(self) -> List[RequirementEvaluation]:
        return [e for e in self.evaluations if e.is_outstanding()]

    def all_requirements_satisfied(self) -> bool:
        return all(e.is_satisfied() for e in self.evaluations)


def _latest_review_per_reviewer(reviews: Iterable[Review]) -> Dict[str, Review]:
    latest: Dict[str, Review] = {}
    for review in reviews:
        if review.state() not in DECISIVE_STATES:
            continue
        login = review.author_handle()
        if login not in latest or review.submitted_at() > latest[login].submitted_at():
            latest[login] = review
    return latest


def primary_review(
    pull_request: PullRequest, summary: CodeownerSummary
) -> Optional[Review]:
    """The approval that counts as the primary (non-codeowner) review, if any."""
    author = pull_request.author_handle()
    candidates: List[Review] = []
    for login, review in _latest_review_per_reviewer(pull_request.reviews()).items():
        if login == author or login in SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS:
            continue
        if review.state() is not ReviewState.APPROVED:
            continue
        is_codeowner = login in summary.codeowner_logins
        if is_codeowner and login not in summary.human_chosen_logins:
            continue
        candidates.append(review)
    if not candidates:
        return None
    return max(candidates, key=lambda r: r.submitted_at())


def has_primary_review(pull_request: PullRequest, summary: CodeownerSummary) -> bool:
    return primary_review(pull_request, summary) is not None


def review_status(
    pull_request: PullRequest, summary: Optional[CodeownerSummary]
) -> str:
    """Value of the PR task's "Review Status" field.

    Without codeowned files this is SGTM's existing rule. With them: Approved
    only once the primary review is in and every codeowner requirement is
    satisfied; Needs Codeowner Approval when the primary review is in and
    codeowner approvals are outstanding; Needs Review otherwise. A request for
    changes as the latest review wins in both cases.
    """
    if pull_request.is_draft():
        return "Not Ready"
    if summary is None or not summary.has_codeowned_files():
        if pull_request.is_needs_review():
            return "Needs Review"
        return "Approved" if pull_request.is_approved() else "Changes Requested"

    if not pull_request.is_needs_review() and not pull_request.is_approved():
        return "Changes Requested"
    if not has_primary_review(pull_request, summary):
        return "Needs Review"
    if summary.all_requirements_satisfied():
        return "Approved"
    return REVIEW_STATUS_NEEDS_CODEOWNER_APPROVAL
