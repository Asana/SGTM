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

    def test_nobody_available_escalates(self):
        choice = _choose(is_out_of_office=lambda login: True)
        self.assertIsNone(choice.login)
        self.assertEqual(choice.reason, REASON_NOBODY_AVAILABLE)


class TestIdle(unittest.TestCase):
    FRI = datetime(2026, 9, 11, 15, tzinfo=timezone.utc)
    SAT = datetime(2026, 9, 12, 9, tzinfo=timezone.utc)
    MON = datetime(2026, 9, 14, 9, tzinfo=timezone.utc)
    TUE = datetime(2026, 9, 15, 9, tzinfo=timezone.utc)

    def test_weekends_are_skipped(self):
        self.assertEqual(business_days_between(self.FRI, self.SAT), 0)
        self.assertEqual(business_days_between(self.FRI, self.MON), 1)
        self.assertEqual(business_days_between(self.FRI, self.TUE), 2)
        self.assertEqual(business_days_between(self.MON, self.MON), 0)
        self.assertEqual(business_days_between(self.MON, self.FRI), 0)

    def test_is_idle(self):
        self.assertFalse(is_idle(self.FRI, self.SAT, 1, engaged=False))
        self.assertTrue(is_idle(self.FRI, self.MON, 1, engaged=False))
        self.assertFalse(is_idle(self.FRI, self.MON, 1, engaged=True))
        self.assertFalse(is_idle(self.FRI, self.MON, 2, engaged=False))
        self.assertFalse(is_idle(self.FRI, self.TUE, 0, engaged=False))


if __name__ == "__main__":
    unittest.main()
