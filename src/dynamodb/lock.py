from typing import Optional
from datetime import timedelta
import boto3  # type: ignore
from contextlib import contextmanager
from src.config import LOCK_TABLE
from python_dynamodb_lock.python_dynamodb_lock import DynamoDBLockClient  # type: ignore


dynamodb_resource = boto3.resource("dynamodb")


@contextmanager
def dynamodb_lock(pull_request_id: str, retry_timeout: Optional[timedelta] = None):
    lock_client = DynamoDBLockClient(
        dynamodb_resource,
        table_name=LOCK_TABLE,
        # partition_key_name="key",
        # sort_key_name="key",
    )

    # TODO: Make this match get-lock-client in the clojure code
    lock = lock_client.acquire_lock(
        pull_request_id, sort_key=pull_request_id, retry_timeout=retry_timeout
    )
    try:
        yield lock
    finally:
        lock.release(best_effort=True)
