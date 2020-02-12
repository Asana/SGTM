import boto3
from test.mock_dynamodb_test_case import MockDynamoDbTestCase
from src.config import USERS_TABLE
from src.dynamodb import client as dynamodb_client


class DynamodbClientTest(MockDynamoDbTestCase):
    def test_get_asana_id_from_github_node_id_and_insert_github_node_to_asana_id_mapping(
        self,
    ):
        gh_node_id = "abcdefg"
        asana_id = "123456"

        # First, no mapping exists
        self.assertEqual(
            dynamodb_client.get_asana_id_from_github_node_id(gh_node_id), None
        )
        # Then, add the mapping
        dynamodb_client.insert_github_node_to_asana_id_mapping(gh_node_id, asana_id)
        # Now we get the asana_id
        self.assertEqual(
            dynamodb_client.get_asana_id_from_github_node_id(gh_node_id), asana_id
        )

    def test_get_asana_domain_user_id_from_github_handle(self):
        client = boto3.client("dynamodb")

        gh_handle = "Elaine Benes"
        asana_user_id = "12345"
        client.put_item(
            TableName=USERS_TABLE,
            Item={
                "github/handle": {"S": gh_handle},
                "asana/domain-user-id": {"S": asana_user_id},
            },
        )

        self.assertEqual(
            dynamodb_client.get_asana_domain_user_id_from_github_handle(gh_handle),
            asana_user_id,
        )
