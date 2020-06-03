import unittest
from mock import patch

from src.sync_users.sgtm_user import SgtmUser
from src.dynamodb.client import DynamoDbClient


class TestSgtmUser(unittest.TestCase):
    def test_constructor_lower_cases_github_handle(self):
        user = SgtmUser("JerrySeinfeld", "123")
        self.assertEqual(user.github_handle, "jerryseinfeld")

    def test_constructor_handles_None(self):
        user = SgtmUser(None, None)
        self.assertEqual(user.github_handle, None)
        self.assertEqual(user.domain_user_id, None)

    def test_from_custom_fields_list__creates_user(self):
        custom_fields = [
            {
                "name": SgtmUser.GITHUB_HANDLE_CUSTOM_FIELD_NAME,
                "type": "text",
                "text_value": "elainebenes",
            },
            {
                "name": SgtmUser.USER_ID_CUSTOM_FIELD_NAME,
                "type": "number",
                "number_value": 123,
            },
        ]
        user = SgtmUser.from_custom_fields_list(custom_fields)
        self.assertEqual(user.github_handle, "elainebenes")
        self.assertEqual(user.domain_user_id, "123")

    def test_from_custom_fields_list__empty_value_returns_None(self):
        custom_fields = [
            {
                "name": SgtmUser.GITHUB_HANDLE_CUSTOM_FIELD_NAME,
                "type": "text",
                "text_value": "",  # Empty string
            },
            {
                "name": SgtmUser.USER_ID_CUSTOM_FIELD_NAME,
                "type": "number",
                "number_value": 123,
            },
        ]
        user = SgtmUser.from_custom_fields_list(custom_fields)
        self.assertEqual(user, None)

    def test_from_custom_fields_list__missing_custom_fields_returns_None(self):
        custom_fields = [
            {"name": "some-unknown_custom-field", "type": "text", "text_value": "foo",},
            {
                "name": SgtmUser.USER_ID_CUSTOM_FIELD_NAME,
                "type": "number",
                "number_value": 123,
            },
        ]
        user = SgtmUser.from_custom_fields_list(custom_fields)
        self.assertEqual(user, None)

    def test_equality(self):
        user1 = SgtmUser("Foo", "123")
        user2 = SgtmUser("fOO", "123")
        self.assertEqual(user1, user2)


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
