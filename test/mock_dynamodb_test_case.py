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
    def setUpClass(kls):
        with mock_dynamodb2():
            client = boto3.client("dynamodb")

            client.create_table(
                AttributeDefinitions=[
                    {"AttributeName": "github-node", "AttributeType": "S",}
                ],
                TableName=OBJECTS_TABLE,
                KeySchema=[{"AttributeName": "github-node", "KeyType": "HASH",}],
            )

            client.create_table(
                AttributeDefinitions=[
                    {"AttributeName": "github/handle", "AttributeType": "S",}
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
