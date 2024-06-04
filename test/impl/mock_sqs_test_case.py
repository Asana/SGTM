"""
Test case that should be used for tests that require integration with dynamodb
or other external resources.
"""
import os
import boto3  # type: ignore
from moto import mock_sqs  # type: ignore
from src.config import AWS_REGION
from .base_test_case_class import BaseClass

# "Mock" the AWS credentials as they can't be mocked in Botocore currently
os.environ.setdefault("AWS_ACCESS_KEY_ID", "foobar_key")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "foobar_secret")


@mock_sqs
class MockSQSTestCase(BaseClass):

    """
    The boto3.client instance, mocked by moto, that should be used in the tests.
    """

    client = None
    test_queue_name = "test-queue.fifo"
    test_queue_url = None

    @classmethod
    def tearDownClass(cls):
        cls.client = None
        cls.test_queue_url = None

        mock_sqs().__exit__()

    @classmethod
    def setUpClass(cls):
        mock_sqs().__enter__()

        client = boto3.client("sqs", region_name=AWS_REGION)

        client.create_queue(
            QueueName=cls.test_queue_name,
            Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
        )

        cls.test_queue_url = client.get_queue_url(QueueName=cls.test_queue_name)[
            "QueueUrl"
        ]
        cls.client = client
