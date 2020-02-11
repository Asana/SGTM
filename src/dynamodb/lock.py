import boto3
from contextlib import contextmanager
from src.config import LOCK_TABLE
from python_dynamodb_lock.python_dynamodb_lock import DynamoDBLockClient


dynamodb_resource = boto3.resource("dynamodb")


def dynamodb_lock(pull_request_id: str):
    lock_client = DynamoDBLockClient(
        dynamodb_resource,
        table_name=LOCK_TABLE,
        # partition_key_name="key",
        # sort_key_name="key",
    )
    # TODO: Make this match get-lock-client in the clojure code
    return lock_client.acquire_lock(pull_request_id, sort_key=pull_request_id)
