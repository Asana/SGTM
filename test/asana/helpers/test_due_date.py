from datetime import datetime
from src.asana import helpers as asana_helpers

from test.impl.base_test_case_class import BaseClass


class TestDefaultDueDateStr(BaseClass):
    def test_default_due_date_str_from_mid_week(self):
        thursday = datetime(2020, 4, 9)
        self.assertEqual(asana_helpers.default_due_date_str(thursday), "2020-04-10")

    def test_default_due_date_str_if_tomorrow_is_weekend(self):
        friday = datetime(2020, 4, 10)
        saturday = datetime(2020, 4, 11)

        self.assertEqual(asana_helpers.default_due_date_str(friday), "2020-04-13")
        self.assertEqual(asana_helpers.default_due_date_str(saturday), "2020-04-13")


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
