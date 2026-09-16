"""Pick who a codeowner subtask is assigned to, and when to pick again."""
import random
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Optional, Set

# User-facing phrases completing "Assigned to @X, ...". Kept here so the task
# description and tests agree on the exact wording.
REASON_HUMAN_REQUESTED = "who was already requested as a reviewer on this PR"
REASON_ENGAGED = "who has already reviewed this PR"
REASON_RANDOM = (
    "picked at random from the available codeowners (the PR author and anyone "
    "out of office in Asana are skipped)"
)
REASON_NOBODY_AVAILABLE = (
    "No available codeowner: everyone is the PR author or out of office. "
    "Assigned to the PR author to find a reviewer."
)


@dataclass(frozen=True)
class AssigneeChoice:
    # None when nobody in the pool is available; the caller escalates.
    login: Optional[str]
    reason: str


def choose_assignee(
    pool: Set[str],
    author: str,
    is_out_of_office: Callable[[str], bool],
    has_asana_mapping: Callable[[str], bool],
    human_requested_reviewers: Set[str],
    engaged_logins: Set[str],
    exclude: Optional[Set[str]] = None,
    rng: Optional[random.Random] = None,
) -> AssigneeChoice:
    """Choose a codeowner for a subtask.

    Preference order: someone a person already asked to review, then someone
    who already reviewed or commented, then a random pick. The author, anyone
    out of office, anyone without an Asana account mapping and anyone in
    `exclude` (a previous assignee being replaced) are never chosen.
    """
    rng = rng or random.Random()
    excluded = set(exclude or set()) | {author}
    eligible = sorted(
        login
        for login in pool
        if login not in excluded
        and has_asana_mapping(login)
        and not is_out_of_office(login)
    )
    if not eligible:
        return AssigneeChoice(None, REASON_NOBODY_AVAILABLE)
    requested = [login for login in eligible if login in human_requested_reviewers]
    if requested:
        return AssigneeChoice(rng.choice(requested), REASON_HUMAN_REQUESTED)
    engaged = [login for login in eligible if login in engaged_logins]
    if engaged:
        return AssigneeChoice(rng.choice(engaged), REASON_ENGAGED)
    return AssigneeChoice(rng.choice(eligible), REASON_RANDOM)


def business_days_between(start: datetime, end: datetime) -> int:
    """Whole weekdays (Mon-Fri, by UTC date) after `start`'s date up to `end`'s date.

    Holidays are not tracked; vacations rely on Asana out-of-office.
    """
    if end <= start:
        return 0
    days = 0
    day: date = start.date()
    while day < end.date():
        day = date.fromordinal(day.toordinal() + 1)
        if day.weekday() < 5:
            days += 1
    return days


def is_idle(
    assigned_at: datetime, now: datetime, idle_business_days: int, engaged: bool
) -> bool:
    """True when the assignee has gone `idle_business_days` business days
    without reviewing or commenting since being assigned."""
    if engaged or idle_business_days <= 0:
        return False
    return business_days_between(assigned_at, now) >= idle_business_days
