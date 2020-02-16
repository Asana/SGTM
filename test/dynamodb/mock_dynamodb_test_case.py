"""
Test case that should be used for tests that require integration with dynamodb
or other external resources.
"""
from unittest import TestCase
import boto3

from moto import mock_dynamodb2
from src.config import OBJECTS_TABLE, USERS_TABLE, LOCK_TABLE


@mock_dynamodb2
class MockDynamoDbTestCase(TestCase):

    @classmethod
    def tearDownClass(cls):
        mock_dynamodb2().__exit__()

    @classmethod
    def setUpClass(cls):
        mock_dynamodb2().__enter__()
        client = boto3.client("dynamodb")
        cls.client = client

        client.create_table(
            AttributeDefinitions=[
                {"AttributeName": "github-node", "AttributeType": "S",}
            ],
            TableName=OBJECTS_TABLE,
            KeySchema=[{"AttributeName": "github-node", "KeyType": "HASH",}],
        )

        client.create_table(
            AttributeDefinitions=[
                {"AttributeName": "github/handle", "AttributeType": "S",},
                {"AttributeName": "asana/domain-user-id", "AttributeType": "S",}
            ],
            TableName=USERS_TABLE,
            KeySchema=[{"AttributeName": "github/handle", "KeyType": "HASH",}],
        )

        client.create_table(
            AttributeDefinitions=[
                {"AttributeName": "lock_key", "AttributeType": "S",},
                {"AttributeName": "sort_key", "AttributeType": "S",},
            ],
            TableName=LOCK_TABLE,
            KeySchema=[
                {"AttributeName": "lock_key", "KeyType": "HASH",},
                {"AttributeName": "sort_key", "KeyType": "RANGE",},
            ],
        )

    @classmethod
    def insert_test_user_into_user_table(cls, login, asana_domain_user_id):
        cls.client.put_item(
            TableName=USERS_TABLE,
            Item={
                "github/handle": {"S": login},
                "asana/domain-user-id": {"S": asana_domain_user_id},
            },
        )