from typing import Optional
from datetime import timedelta
import boto3  # type: ignore
from contextlib import contextmanager
from src.config import LOCK_TABLE
from python_dynamodb_lock.python_dynamodb_lock import DynamoDBLockClient  # type: ignore


dynamodb_resource = boto3.resource("dynamodb")

lock_client = DynamoDBLockClient(
    dynamodb_resource,
    table_name=LOCK_TABLE,
    expiry_period=timedelta(
        minutes=2
    ),  # The Lambda function has a 120 second timeout by default
    # partition_key_name="key",
    # sort_key_name="key",
)


@contextmanager
def dynamodb_lock(
    lock_name: str, retry_timeout: Optional[timedelta] = timedelta(seconds=20)
):
    # TODO: Make this match get-lock-client in the clojure code
    lock = lock_client.acquire_lock(
        lock_name, sort_key=lock_name, retry_timeout=retry_timeout
    )
    try:
        yield lock
    finally:
        lock.release(best_effort=True)
