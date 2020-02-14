from typing import Optional
import boto3
from src.config import OBJECTS_TABLE, USERS_TABLE
from botocore.exceptions import NoRegionError
from src.utils import memoize


class ConfigurationError(Exception):
    pass


_client = None


def get_singleton():
    global _client
    if _client is not None:
        return _client
    try:
        _client = boto3.client("dynamodb")
        return _client
    except NoRegionError:
        pass
    # by raising the new error outside of the except clause, the ConfigurationError does not automatically contain
    # the stack trace of the NoRegionError, which provides no extra value and clutters the console.
    raise ConfigurationError("Configuration error: Please select a region, e.g. via `AWS_DEFAULT_REGION=us-east-1`")


def set_singleton(client):
    global _client
    _client = client


### OBJECTS TABLE


def get_asana_id_from_github_node_id(gh_node_id: str) -> Optional[str]:
    response = get_singleton().get_item(
        TableName=OBJECTS_TABLE, Key={"github-node": {"S": gh_node_id}}
    )
    if "Item" in response:
        return response["Item"]["asana-id"]["S"]
    else:
        return None


def insert_github_node_to_asana_id_mapping(gh_node_id: str, asana_id: str):
    response = get_singleton().put_item(
        TableName=OBJECTS_TABLE,
        Item={"github-node": {"S": gh_node_id}, "asana-id": {"S": asana_id}},
    )


### USERS TABLE


@memoize
def get_asana_domain_user_id_from_github_handle(github_handle: str) -> Optional[str]:
    response = get_singleton().get_item(
        TableName=USERS_TABLE, Key={"github/handle": {"S": github_handle}}
    )
    if "Item" in response:
        return response["Item"]["asana/domain-user-id"]["S"]
    else:
        return None
