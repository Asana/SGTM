from typing import Optional
import boto3
from src.config import OBJECTS_TABLE, USERS_TABLE
from botocore.exceptions import NoRegionError
from src.utils import memoize


class ConfigurationError(Exception):
    pass


def _create_client():
    try:
        return boto3.client("dynamodb")
    except NoRegionError:
        pass
    # by raising the new error outside of the except clause, the ConfigurationError does not automatically contain
    # the stack trace of the NoRegionError, which provides no extra value and clutters the console.
    raise ConfigurationError("Configuration error: Please select a region, e.g. via `AWS_DEFAULT_REGION=us-east-1`")


class DynamoDbClient(object):

    def __init__(self):
        self.client = _create_client()

    # OBJECTS TABLE
    def get_asana_id_from_github_node_id(self, gh_node_id: str) -> Optional[str]:
        response = self.client.get_item(
            TableName=OBJECTS_TABLE, Key={"github-node": {"S": gh_node_id}}
        )
        if "Item" in response:
            return response["Item"]["asana-id"]["S"]
        else:
            return None

    def insert_github_node_to_asana_id_mapping(self, gh_node_id: str, asana_id: str):
        response = self.client.put_item(
            TableName=OBJECTS_TABLE,
            Item={"github-node": {"S": gh_node_id}, "asana-id": {"S": asana_id}},
        )

    # USERS TABLE

    @memoize
    def get_asana_domain_user_id_from_github_handle(self, github_handle: str) -> Optional[str]:
        response = self.client.get_item(
            TableName=USERS_TABLE, Key={"github/handle": {"S": github_handle}}
        )
        if "Item" in response:
            return response["Item"]["asana/domain-user-id"]["S"]
        else:
            return None


_dynamodb_client = None


def inject(dynamodb_client):
    global _dynamodb_client
    _dynamodb_client = dynamodb_client


def _singleton():
    global _dynamodb_client
    if _dynamodb_client is None:
        _dynamodb_client = DynamoDbClient()
    return _dynamodb_client


def get_asana_id_from_github_node_id(*args, **keywords):
    return _singleton().get_asana_id_from_github_node_id(*args, **keywords)


def insert_github_node_to_asana_id_mapping(*args, **keywords):
    return _singleton().insert_github_node_to_asana_id_mapping(*args, **keywords)


def get_asana_domain_user_id_from_github_handle(*args, **keywords):
    return _singleton().get_asana_domain_user_id_from_github_handle(*args, **keywords)
