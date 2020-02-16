from typing import List

from test.dynamodb.mock_dynamodb_test_case import MockDynamoDbTestCase


class BaseClass(MockDynamoDbTestCase):

    def assertContainsStrings(self, actual: str, expected_strings: List[str], field_name: str = None):
        if field_name is None:
            message = f"Expected '{actual}' to contain {{}}"
        else:
            message = f"Expected {field_name} to contain {{}}"
        for expected in expected_strings:
            self.assertIn(expected, actual, message.format(expected))
