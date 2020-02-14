from typing import List
from unittest import TestCase

from test.asana.helpers.dynamodb_client import DynamoDbClient


class BaseClass(TestCase):
    def setUp(self):
        DynamoDbClient.initialize()

    def tearDown(self):
        DynamoDbClient.finalize()

    def assertContainsStrings(self, actual: str, expected_strings: List[str], field_name: str = None):
        if field_name is None:
            message = f"Expected '{actual}' to contain {{}}"
        else:
            message = f"Expected {field_name} to contain {{}}"
        for expected in expected_strings:
            self.assertIn(expected, actual, message.format(expected))
