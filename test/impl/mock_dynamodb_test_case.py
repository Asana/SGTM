"""
Test case that should be used for tests that require integration with dynamodb
or other external resources.
"""
import os
import boto3  # type: ignore
from moto import mock_dynamodb  # type: ignore
from src.config import AWS_REGION, OBJECTS_TABLE, LOCK_TABLE
from .base_test_case_class import BaseClass

# "Mock" the AWS credentials as they can't be mocked in Botocore currently
os.environ.setdefault("AWS_ACCESS_KEY_ID", "foobar_key")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "foobar_secret")


@mock_dynamodb
class MockDynamoDbTestCase(BaseClass):

    """
    The boto3.client instance, mocked by moto, that should be used in the tests.
    """

    client = None

    """
        The test data helper, which knows how to interact with our dynamodb tables for the purpose
        of test data
    """
    READ_CAPACITY_UNITS = 123
    WRITE_CAPACITY_UNITS = 123

    @classmethod
    def tearDownClass(cls):
        cls.client = None
        mock_dynamodb().__exit__()

    @classmethod
    def setUpClass(cls):
        mock_dynamodb().__enter__()

        client = boto3.client("dynamodb", region_name=AWS_REGION)

        # our DynamoDb Schema #DynamoDbSchema
        client.create_table(
            AttributeDefinitions=[
                {
                    "AttributeName": "github-node",
                    "AttributeType": "S",
                }
            ],
            TableName=OBJECTS_TABLE,
            KeySchema=[
                {
                    "AttributeName": "github-node",
                    "KeyType": "HASH",
                }
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits": cls.READ_CAPACITY_UNITS,
                "WriteCapacityUnits": cls.WRITE_CAPACITY_UNITS,
            },
        )

        client.create_table(
            AttributeDefinitions=[
                {
                    "AttributeName": "lock_key",
                    "AttributeType": "S",
                },
                {
                    "AttributeName": "sort_key",
                    "AttributeType": "S",
                },
            ],
            TableName=LOCK_TABLE,
            KeySchema=[
                {
                    "AttributeName": "lock_key",
                    "KeyType": "HASH",
                },
                {
                    "AttributeName": "sort_key",
                    "KeyType": "RANGE",
                },
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits": cls.READ_CAPACITY_UNITS,
                "WriteCapacityUnits": cls.WRITE_CAPACITY_UNITS,
            },
        )
        cls.client = client
