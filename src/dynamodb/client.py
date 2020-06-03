from typing import Optional, List, Tuple

import boto3  # type: ignore
from botocore.exceptions import NoRegionError  # type: ignore

from src.config import OBJECTS_TABLE, USERS_TABLE
from src.logger import logger
from src.utils import memoize


class ConfigurationError(Exception):
    pass


class DynamoDbClient(object):
    """
        Encapsulates DynamoDb client interface, as exposed to the world. There is a single (singleton) instance of
        DynamoDbClient in the process, which is lazily created upon the first request. This pattern supports test code
        that does not require DynamoDb.
    """

    # the singleton instance of DynamoDbClient
    _singleton = None

    def __init__(self):
        self.client = DynamoDbClient._create_client()

    # getter for the singleton
    @classmethod
    def singleton(cls):
        """
        Getter for the DynamoDbClient singleton
        """
        if cls._singleton is None:
            cls._singleton = DynamoDbClient()
        return cls._singleton

    # OBJECTS TABLE

    def get_asana_id_from_github_node_id(self, gh_node_id: str) -> Optional[str]:
        """
            Retrieves the Asana object-id associated with the specified GitHub node-id,
            or None, if no such association exists. Object-table associations are created
            by SGTM via the insert_github_node_to_asana_id_mapping method, below.
        """
        response = self.client.get_item(
            TableName=OBJECTS_TABLE, Key={"github-node": {"S": gh_node_id}}
        )
        if "Item" in response:
            return response["Item"]["asana-id"]["S"]
        else:
            return None

    def insert_github_node_to_asana_id_mapping(self, gh_node_id: str, asana_id: str):
        """
            Creates an association between a GitHub node-id and an Asana object-id
        """
        self.client.put_item(
            TableName=OBJECTS_TABLE,
            Item={"github-node": {"S": gh_node_id}, "asana-id": {"S": asana_id}},
        )

    def bulk_insert_github_node_to_asana_id_mapping(
        self, gh_and_asana_ids: List[Tuple[str, str]]
    ):
        """Insert multiple mappings from github node ids to Asana object ids.
        Equivalent to calling insert_github_node_to_asana_id_mapping repeatedly,
        but in a single request.

        We need to split large requests into batches of 25, since Dynamodb only accepts 25 items at a time.
        https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_BatchWriteItem.html
        """
        BATCH_SIZE = 25
        for batch_start in range(0, len(gh_and_asana_ids), BATCH_SIZE):
            response = self.client.batch_write_item(
                RequestItems={
                    OBJECTS_TABLE: [
                        {
                            "PutRequest": {
                                "Item": {
                                    "github-node": {"S": gh_node_id},
                                    "asana-id": {"S": asana_id},
                                }
                            }
                        }
                        for gh_node_id, asana_id in gh_and_asana_ids[
                            batch_start : batch_start + BATCH_SIZE
                        ]
                    ]
                }
            )
            if response.get("UnprocessedItems"):
                logger.warning(
                    "Failed to insert github-to-asana id mappings: {}".format(
                        response["UnprocessedItems"]
                    )
                )

    # USERS TABLE

    @memoize
    def get_asana_domain_user_id_from_github_handle(
        self, github_handle: str
    ) -> Optional[str]:
        """
            Retrieves the Asana domain user-id associated with a specific GitHub user login, or None,
            if no such association exists. User-id associations are created manually via an external process.
            TODO: document this process, and create scripts to encapsulate it
        """
        response = self.client.get_item(
            TableName=USERS_TABLE, Key={"github/handle": {"S": github_handle.lower()}}
        )
        if "Item" in response:
            return response["Item"]["asana/domain-user-id"]["S"]
        else:
            return None

    @staticmethod
    def _create_client():
        # Encapsulates creating a boto3 client connection for DynamoDb with a more user-friendly error case
        try:
            return boto3.client("dynamodb")
        except NoRegionError:
            pass
        # by raising the new error outside of the except clause, the ConfigurationError does not automatically contain
        # the stack trace of the NoRegionError, which provides no extra value and clutters the console.
        raise ConfigurationError(
            "Configuration error: Please select a region, e.g. via `AWS_DEFAULT_REGION=us-east-1`"
        )


def get_asana_id_from_github_node_id(gh_node_id: str) -> Optional[str]:
    """
        Using the singleton instance of DynamoDbClient, creating it if necessary:

        Retrieves the Asana object-id associated with the specified GitHub node-id,
        or None, if no such association exists. Object-table associations are created
        by SGTM via the insert_github_node_to_asana_id_mapping method, below.
    """
    return DynamoDbClient.singleton().get_asana_id_from_github_node_id(gh_node_id)


def insert_github_node_to_asana_id_mapping(gh_node_id: str, asana_id: str):
    """
        Using the singleton instance of DynamoDbClient, creating it if necessary:

        Creates an association between a GitHub node-id and an Asana object-id
    """
    return DynamoDbClient.singleton().insert_github_node_to_asana_id_mapping(
        gh_node_id, asana_id
    )


def get_asana_domain_user_id_from_github_handle(github_handle: str) -> Optional[str]:
    """
        Using the singleton instance of DynamoDbClient, creating it if necessary:

        Retrieves the Asana domain user-id associated with a specific GitHub user login, or None,
        if no such association exists. User-id associations are created manually via an external process.
    """
    return DynamoDbClient.singleton().get_asana_domain_user_id_from_github_handle(
        github_handle
    )


def bulk_insert_github_node_to_asana_id_mapping(
    gh_and_asana_ids: List[Tuple[str, str]]
):
    """Insert multiple mappings from github node ids to Asana object ids.
    Equivalent to calling insert_github_node_to_asana_id_mapping repeatedly,
    but in a single request.
    """
    DynamoDbClient.singleton().bulk_insert_github_node_to_asana_id_mapping(
        gh_and_asana_ids
    )
