import boto3  # type: ignore
from datetime import timedelta
from src.config import LOCK_TABLE, AWS_REGION
from python_dynamodb_lock.python_dynamodb_lock import DynamoDBLockClient  # type: ignore

# Lazy initialization - these will be created when first accessed
_dynamodb_resource = None
_dynamodb_lock_client = None


def get_dynamodb_resource():
    """Get the DynamoDB resource, creating it lazily on first access."""
    global _dynamodb_resource
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource("dynamodb", region_name=AWS_REGION)
    return _dynamodb_resource


def get_dynamodb_lock_client():
    """Get the DynamoDB lock client, creating it lazily on first access."""
    global _dynamodb_lock_client
    if _dynamodb_lock_client is None:
        _dynamodb_lock_client = DynamoDBLockClient(
            get_dynamodb_resource(),
            table_name=LOCK_TABLE,
            lease_duration=timedelta(seconds=20),
            expiry_period=timedelta(
                minutes=2
            ),  # The Lambda function has a 120 second timeout by default
        )
    return _dynamodb_lock_client


# Create a lazy-loading module-level variable
class _LazyLockClient:
    def __getattr__(self, name):
        return getattr(get_dynamodb_lock_client(), name)


dynamodb_lock_client = _LazyLockClient()
