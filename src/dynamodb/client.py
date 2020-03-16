from typing import Optional
import boto3
from src.config import OBJECTS_TABLE, USERS_TABLE
from src.utils import memoize

client = boto3.client("dynamodb")


### OBJECTS TABLE


def get_asana_id_from_github_node_id(gh_node_id: str) -> Optional[str]:
    response = client.get_item(
        TableName=OBJECTS_TABLE, Key={"github-node": {"S": gh_node_id}}
    )
    if "Item" in response:
        return response["Item"]["asana-id"]["S"]
    else:
        return None


def insert_github_node_to_asana_id_mapping(gh_node_id: str, asana_id: str):
    response = client.put_item(
        TableName=OBJECTS_TABLE,
        Item={"github-node": {"S": gh_node_id}, "asana-id": {"S": asana_id}},
    )


### USERS TABLE


@memoize
def get_asana_domain_user_id_from_github_handle(github_handle: str) -> Optional[str]:
    response = client.get_item(
        TableName=USERS_TABLE, Key={"github/handle": {"S": github_handle.lower()}}
    )
    if "Item" in response:
        return response["Item"]["asana/domain-user-id"]["S"]
    else:
        return None
