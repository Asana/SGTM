import unittest
from mock import patch

from src.asana import client as asana_client
from src.dynamodb import client as dynamodb_client
from src.sync_users.handler import handler
from src.sync_users.sgtm_user import SgtmUser


GITHUB_HANDLE_KEY = dynamodb_client.DynamoDbClient.GITHUB_HANDLE_KEY
USER_ID_KEY = dynamodb_client.DynamoDbClient.USER_ID_KEY


@patch.object(asana_client, "find_all_tasks_for_project")
@patch.object(dynamodb_client, "bulk_insert_github_handle_to_asana_user_id_mapping")
@patch.object(dynamodb_client, "get_all_user_items")
class TestHandler(unittest.TestCase):
    def test_no_users_to_sync__all_already_synced(
        self, get_all_user_items_mock, bulk_insert_mock, find_tasks_mock
    ):
        gh_handle = "torvalds"
        asana_user_id = "12345"
        get_all_user_items_mock.return_value = [
            {GITHUB_HANDLE_KEY: {"S": gh_handle}, USER_ID_KEY: {"S": asana_user_id},}
        ]

        find_tasks_mock.return_value = [
            {
                "gid": "1",
                "custom_fields": [
                    {
                        "name": SgtmUser.GITHUB_HANDLE_CUSTOM_FIELD_NAME,
                        "type": "text",
                        "text_value": gh_handle,
                    },
                    {
                        "name": SgtmUser.USER_ID_CUSTOM_FIELD_NAME,
                        "type": "text",
                        "text_value": asana_user_id,
                    },
                ],
            }
        ]

        handler({}, {})

        # No writes necessary, because all users are in DynamoDb table already
        self.assertEqual(bulk_insert_mock.call_count, 0)

    def test_no_users_to_sync__incomplete_user_info(
        self, get_all_user_items_mock, bulk_insert_mock, find_tasks_mock
    ):
        get_all_user_items_mock.return_value = []

        find_tasks_mock.return_value = [
            {
                "gid": "1",
                "custom_fields": [
                    {
                        "name": SgtmUser.GITHUB_HANDLE_CUSTOM_FIELD_NAME,
                        "type": "text",
                        "text_value": "",  # missing Github Handle
                    },
                    {
                        "name": SgtmUser.USER_ID_CUSTOM_FIELD_NAME,
                        "type": "text",
                        "text_value": "12345",
                    },
                ],
            },
            {
                "gid": "2",
                "custom_fields": [
                    {
                        "name": SgtmUser.GITHUB_HANDLE_CUSTOM_FIELD_NAME,
                        "type": "text",
                        "text_value": "torvalds",
                    },
                    {
                        "name": SgtmUser.USER_ID_CUSTOM_FIELD_NAME,
                        "type": "text",
                        "text_value": "",  # missing Asana user id
                    },
                ],
            },
            {"gid": "3", "custom_fields": []},
        ]

        handler({}, {})

        # No writes necessary, because no users have the mapping values that
        # are required
        self.assertEqual(bulk_insert_mock.call_count, 0)

    def test_sync_users__none_already(
        self, get_all_user_items_mock, bulk_insert_mock, find_tasks_mock
    ):
        # No existing dynamodb user mappings
        get_all_user_items_mock.return_value = []

        find_tasks_mock.return_value = [
            {
                "gid": "1",
                "custom_fields": [
                    {
                        "name": SgtmUser.GITHUB_HANDLE_CUSTOM_FIELD_NAME,
                        "type": "text",
                        "text_value": "user1",
                    },
                    {
                        "name": SgtmUser.USER_ID_CUSTOM_FIELD_NAME,
                        "type": "text",
                        "text_value": "123",
                    },
                ],
            },
            {
                "gid": "2",
                "custom_fields": [
                    {
                        "name": SgtmUser.GITHUB_HANDLE_CUSTOM_FIELD_NAME,
                        "type": "text",
                        "text_value": "user2",
                    },
                    {
                        "name": SgtmUser.USER_ID_CUSTOM_FIELD_NAME,
                        "type": "text",
                        "text_value": "456",
                    },
                ],
            },
        ]

        handler({}, {})

        # All users should be written
        self.assertEqual(bulk_insert_mock.call_count, 1)
        bulk_insert_mock.assert_called_with([("user1", "123"), ("user2", "456")])

    def test_sync_users__partial(
        self, get_all_user_items_mock, bulk_insert_mock, find_tasks_mock
    ):
        # user1 already exists in the DynamoDb mapping table
        get_all_user_items_mock.return_value = [
            {GITHUB_HANDLE_KEY: {"S": "user1"}, USER_ID_KEY: {"S": "123"},}
        ]

        find_tasks_mock.return_value = [
            {
                "gid": "1",
                "custom_fields": [
                    {
                        "name": SgtmUser.GITHUB_HANDLE_CUSTOM_FIELD_NAME,
                        "type": "text",
                        "text_value": "user1",
                    },
                    {
                        "name": SgtmUser.USER_ID_CUSTOM_FIELD_NAME,
                        "type": "text",
                        "text_value": "123",
                    },
                ],
            },
            {
                "gid": "2",
                "custom_fields": [
                    {
                        "name": SgtmUser.GITHUB_HANDLE_CUSTOM_FIELD_NAME,
                        "type": "text",
                        "text_value": "user2",
                    },
                    {
                        "name": SgtmUser.USER_ID_CUSTOM_FIELD_NAME,
                        "type": "text",
                        "text_value": "456",
                    },
                ],
            },
        ]

        handler({}, {})

        # only user2 should be written
        self.assertEqual(bulk_insert_mock.call_count, 1)
        bulk_insert_mock.assert_called_with([("user2", "456")])


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
