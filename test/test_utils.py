import unittest

from src.utils import memoize, parse_date_string


class TestParseDateString(unittest.TestCase):
    def test_parse_date_string(self):
        date_strings = [
            "2020-02-22T01:02:03+00:00",
            "2020-02-22T01:02:03+0000",
            "2020-02-22T01:02:03Z",
        ]
        for date_string in date_strings:
            dt = parse_date_string(date_string)
            self.assertEqual(2020, dt.year)
            self.assertEqual(2, dt.month)
            self.assertEqual(22, dt.day)
            self.assertEqual(1, dt.hour)
            self.assertEqual(2, dt.minute)
            self.assertEqual(3, dt.second)


class TestMemoize(unittest.TestCase):
    def test_decorated_functions_should_always_return_the_same_value(self):
        tmp_remember_me = 0

        @memoize
        def remember_me():
            nonlocal tmp_remember_me
            tmp_remember_me += 1
            return tmp_remember_me

        self.assertEqual(1, remember_me(), "Expected remember_me to initially return 1")
        self.assertEqual(
            1,
            remember_me(),
            "Expected remember_me to always return 1 due to memoization",
        )


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
