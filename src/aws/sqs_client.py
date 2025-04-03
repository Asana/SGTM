import boto3  # type: ignore
import json
from typing import List, Optional

from src.config import (
    AWS_REGION,
    SQS_URL,
)
from src.logger import logger


class SQSClient(object):
    """
    Encapsulates SQS client interface, as exposed to the world. There is a single (singleton) instance of
    SQSClient in the process, which is lazily created upon the first request.
    """

    # the singleton instance of SQSClient
    _singleton = None

    def __init__(self):
        self.sqs_client = SQSClient._create_sqs_client()

    # getter for the singleton
    @classmethod
    def singleton(cls):
        """
        Getter for the SQSClient singleton
        """
        if cls._singleton is None:
            cls._singleton = SQSClient()
        return cls._singleton

    @staticmethod
    def _create_sqs_client():
        return boto3.client("sqs", region_name=AWS_REGION)

    def send_message(
        self,
        queue_url: str,
        message_body: str,
        message_group_id: str,
        message_attributes: Optional[dict] = None,
    ):
        """
        Sends a message to the specified SQS queue
        """
        response = self.sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=message_body,
            MessageGroupId=message_group_id,
            MessageAttributes=message_attributes,
        )
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            logger.info(f"Sent message to SQS queue {queue_url}")
        else:
            logger.error(
                f"Error sending message to SQS queue {queue_url}, response {response}"
            )

    def receive_messages(
        self, queue_url: str, max_number_of_messages: int = 1
    ) -> List[dict]:
        """
        Receives messages from the specified SQS queue
        """
        response = self.sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_number_of_messages,
        )
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            logger.info(f"Received messages from SQS queue {queue_url}")
            return response.get("Messages", [])
        else:
            logger.error(
                f"Error receiving messages from SQS queue {queue_url}, response {response}"
            )
            return []


def queue_new_event(event_type: str, body: str):
    """
    Using the singleton instance of SQSClient, creating it if necessary:

    Sends a message to the specified SQS queue
    """
    logger.info(f"Queueing event {event_type} to SQS queue {SQS_URL}")
    SQSClient.singleton().send_message(
        queue_url=SQS_URL,
        message_body=body,
        message_group_id="fifo_group_id",  # single group id for all messages
        message_attributes={
            "X-GitHub-Event": {"DataType": "String", "StringValue": event_type},
        },
    )


def queue_full_sync(pull_request_id: str, organization: str):
    body = {
        "pull_request": {"node_id": pull_request_id},
        "organization": {"login": organization},
    }
    queue_new_event("pull_request", json.dumps(body))
