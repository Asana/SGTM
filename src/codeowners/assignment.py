"""Pick who a codeowner subtask is assigned to, and when to pick again."""
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Callable, Dict, List, Optional, Set

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
    candidates = sorted(login for login in pool if login not in excluded)

    # Mapping and out-of-office lookups cost an S3 / Asana call each, so they
    # run lazily, in preference order, and stop at the first available person.
    availability: Dict[str, bool] = {}

    def available(login: str) -> bool:
        if login not in availability:
            availability[login] = has_asana_mapping(login) and not is_out_of_office(
                login
            )
        return availability[login]

    tiers: List["tuple[Optional[Set[str]], str]"] = [
        (human_requested_reviewers, REASON_HUMAN_REQUESTED),
        (engaged_logins, REASON_ENGAGED),
        (None, REASON_RANDOM),
    ]
    for members, reason in tiers:
        tier = [login for login in candidates if members is None or login in members]
        rng.shuffle(tier)
        for login in tier:
            if available(login):
                return AssigneeChoice(login, reason)
    return AssigneeChoice(None, REASON_NOBODY_AVAILABLE)


def business_days_between(start: datetime, end: datetime) -> int:
    """Business days (Mon-Fri, by UTC date) elapsed from `start` to `end`.

    A weekday counts once `end` has reached `start`'s time of day on it, so an
    assignment late in the UTC day is not "a day idle" a few minutes later:
    Friday 15:00 -> Monday 09:00 is 0, Monday 15:00 is 1, Tuesday 15:00 is 2.
    Holidays are not tracked; vacations rely on Asana out-of-office.
    """
    if end <= start:
        return 0
    days = 0
    day: date = start.date() + timedelta(days=1)
    while day <= end.date():
        if day.weekday() < 5 and end >= datetime.combine(day, start.timetz()):
            days += 1
        day += timedelta(days=1)
    return days


def is_idle(
    assigned_at: datetime, now: datetime, idle_business_days: int, engaged: bool
) -> bool:
    """True when the assignee has gone `idle_business_days` business days
    without reviewing or commenting since being assigned."""
    if engaged or idle_business_days <= 0:
        return False
    return business_days_between(assigned_at, now) >= idle_business_days
