import random
import unittest
from datetime import datetime, timezone

from src.codeowners.assignment import (
    REASON_ENGAGED,
    REASON_HUMAN_REQUESTED,
    REASON_NOBODY_AVAILABLE,
    REASON_RANDOM,
    business_days_between,
    choose_assignee,
    is_idle,
)


def _choose(**overrides):
    kwargs = dict(
        pool={"a", "b", "c", "d"},
        author="z",
        is_out_of_office=lambda login: False,
        has_asana_mapping=lambda login: True,
        human_requested_reviewers=set(),
        engaged_logins=set(),
        rng=random.Random(42),
    )
    kwargs.update(overrides)
    return choose_assignee(**kwargs)


class TestChooseAssignee(unittest.TestCase):
    def test_excludes_author_ooo_unmapped_and_previous_assignee(self):
        choice = _choose(
            author="a",
            is_out_of_office=lambda login: login == "b",
            has_asana_mapping=lambda login: login != "c",
            exclude={"d"},
            pool={"a", "b", "c", "d", "e"},
        )
        self.assertEqual(choice.login, "e")
        self.assertEqual(choice.reason, REASON_RANDOM)

    def test_prefers_human_requested_then_engaged(self):
        self.assertEqual(
            _choose(human_requested_reviewers={"b"}, engaged_logins={"c"}).login, "b"
        )
        self.assertEqual(
            _choose(human_requested_reviewers={"b"}, engaged_logins={"c"}).reason,
            REASON_HUMAN_REQUESTED,
        )
        choice = _choose(engaged_logins={"c"})
        self.assertEqual(choice.login, "c")
        self.assertEqual(choice.reason, REASON_ENGAGED)

    def test_human_requested_author_does_not_count(self):
        choice = _choose(author="b", human_requested_reviewers={"b"})
        self.assertNotEqual(choice.login, "b")
        self.assertEqual(choice.reason, REASON_RANDOM)

    def test_random_pick_is_reproducible(self):
        first = _choose(rng=random.Random(7)).login
        second = _choose(rng=random.Random(7)).login
        self.assertEqual(first, second)

    def test_availability_is_checked_lazily_in_preference_order(self):
        checked = []

        def is_out_of_office(login):
            checked.append(login)
            return False

        choice = _choose(
            human_requested_reviewers={"b"}, is_out_of_office=is_out_of_office
        )
        self.assertEqual(choice.login, "b")
        self.assertEqual(checked, ["b"])

    def test_nobody_available_escalates(self):
        choice = _choose(is_out_of_office=lambda login: True)
        self.assertIsNone(choice.login)
        self.assertEqual(choice.reason, REASON_NOBODY_AVAILABLE)


class TestIdle(unittest.TestCase):
    FRI = datetime(2026, 9, 11, 15, tzinfo=timezone.utc)
    SAT = datetime(2026, 9, 12, 9, tzinfo=timezone.utc)
    MON_AM = datetime(2026, 9, 14, 9, tzinfo=timezone.utc)
    MON_PM = datetime(2026, 9, 14, 16, tzinfo=timezone.utc)
    TUE_AM = datetime(2026, 9, 15, 9, tzinfo=timezone.utc)
    TUE_PM = datetime(2026, 9, 15, 16, tzinfo=timezone.utc)

    def test_weekends_are_skipped_and_days_count_once_fully_elapsed(self):
        self.assertEqual(business_days_between(self.FRI, self.SAT), 0)
        self.assertEqual(business_days_between(self.FRI, self.MON_AM), 0)
        self.assertEqual(business_days_between(self.FRI, self.MON_PM), 1)
        self.assertEqual(business_days_between(self.FRI, self.TUE_AM), 1)
        self.assertEqual(business_days_between(self.FRI, self.TUE_PM), 2)
        self.assertEqual(business_days_between(self.MON_AM, self.MON_AM), 0)
        self.assertEqual(business_days_between(self.MON_AM, self.FRI), 0)

    def test_a_late_assignment_is_not_idle_minutes_later(self):
        late = datetime(2026, 9, 14, 23, 0, tzinfo=timezone.utc)
        self.assertEqual(
            business_days_between(
                late, datetime(2026, 9, 15, 0, 30, tzinfo=timezone.utc)
            ),
            0,
        )
        self.assertEqual(
            business_days_between(
                late, datetime(2026, 9, 15, 23, 30, tzinfo=timezone.utc)
            ),
            1,
        )

    def test_is_idle(self):
        self.assertFalse(is_idle(self.FRI, self.SAT, 1, engaged=False))
        self.assertFalse(is_idle(self.FRI, self.MON_AM, 1, engaged=False))
        self.assertTrue(is_idle(self.FRI, self.MON_PM, 1, engaged=False))
        self.assertFalse(is_idle(self.FRI, self.MON_PM, 1, engaged=True))
        self.assertFalse(is_idle(self.FRI, self.MON_PM, 2, engaged=False))
        self.assertFalse(is_idle(self.FRI, self.TUE_PM, 0, engaged=False))


if __name__ == "__main__":
    unittest.main()
