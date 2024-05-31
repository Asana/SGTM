import boto3  # type: ignore
from datetime import timedelta
from src.config import AWS_REGION, LOCK_TABLE
from python_dynamodb_lock.python_dynamodb_lock import DynamoDBLockClient  # type: ignore


dynamodb_resource = boto3.resource("dynamodb", region_name=AWS_REGION)

lock_client = DynamoDBLockClient(
    dynamodb_resource,
    table_name=LOCK_TABLE,
    lease_duration=timedelta(seconds=20),
    expiry_period=timedelta(
        minutes=2
    ),  # The Lambda function has a 120 second timeout by default
)
