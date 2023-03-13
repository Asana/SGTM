from unittest import TestCase
from typing import List, Optional


class BaseClass(TestCase):
    def assertContainsStrings(
        self, actual: str, expected_strings: List[str], field_name: Optional[str] = None
    ):
        if field_name is None:
            message = f"Expected '{actual}' to contain {{}}"
        else:
            message = f"Expected {field_name} to contain {{}}"
        for expected in expected_strings:
            self.assertIn(expected, actual, message.format(expected))
