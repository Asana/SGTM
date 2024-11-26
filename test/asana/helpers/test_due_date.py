from datetime import datetime
from src.asana import helpers as asana_helpers

from test.impl.base_test_case_class import BaseClass


class TestDefaultDueDateStr(BaseClass):
    def test_default_due_date_str_same_day(self):
        thursday = datetime(2020, 4, 9)
        self.assertEqual(asana_helpers.default_due_date_str(thursday), "2020-04-09")

    def test_default_due_date_str_from_mid_week(self):
        thursday = datetime(2020, 4, 9, 13)
        self.assertEqual(asana_helpers.default_due_date_str(thursday), "2020-04-10")

    def test_default_due_date_str_if_tomorrow_is_weekend(self):
        friday_morning = datetime(2020, 4, 10, 9)
        friday_afternoon = datetime(2020, 4, 10, 14)
        saturday = datetime(2020, 4, 11)
        sunday = datetime(2020, 4, 12)

        self.assertEqual(
            asana_helpers.default_due_date_str(friday_morning), "2020-04-10"
        )
        self.assertEqual(
            asana_helpers.default_due_date_str(friday_afternoon), "2020-04-13"
        )
        self.assertEqual(asana_helpers.default_due_date_str(saturday), "2020-04-13")
        self.assertEqual(asana_helpers.default_due_date_str(sunday), "2020-04-13")


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
