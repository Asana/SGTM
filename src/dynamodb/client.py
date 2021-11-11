from typing import Iterator, Optional, List, Tuple
from typing_extensions import TypedDict

import boto3  # type: ignore
from botocore.exceptions import NoRegionError  # type: ignore

from src.config import OBJECTS_TABLE, USERS_TABLE
from src.logger import logger
from src.utils import memoize


class DynamoDbItemStringValue(TypedDict):
    S: str


# Unfortunately, we can't use variables for the key names here, so we need to
# use literal strings
DynamoDbUserItem = TypedDict(
    "DynamoDbUserItem",
    {
        "github/handle": DynamoDbItemStringValue,
        "asana/domain-user-id": DynamoDbItemStringValue,
    },
)


class ConfigurationError(Exception):
    pass


class DynamoDbClient(object):
    """
        Encapsulates DynamoDb client interface, as exposed to the world. There is a single (singleton) instance of
        DynamoDbClient in the process, which is lazily created upon the first request. This pattern supports test code
        that does not require DynamoDb.
    """

    GITHUB_HANDLE_KEY = "github/handle"
    USER_ID_KEY = "asana/domain-user-id"

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

    def bulk_insert_items_in_batches(self, table_name: str, items: List[dict]):
        """Insert multiple items to a Dynamodb table.

        We need to split large requests into batches of 25, since Dynamodb only accepts 25 items at a time.
        https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_BatchWriteItem.html
        """
        BATCH_SIZE = 25
        for batch_start in range(0, len(items), BATCH_SIZE):
            response = self.client.batch_write_item(
                RequestItems={
                    table_name: [
                        {"PutRequest": {"Item": item}}
                        for item in items[batch_start : batch_start + BATCH_SIZE]
                    ]
                }
            )
            if response.get("UnprocessedItems"):
                logger.warning(
                    "Failed to insert items: {}".format(response["UnprocessedItems"])
                )

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
        """
        items = [
            {"github-node": {"S": gh_node_id}, "asana-id": {"S": asana_id}}
            for gh_node_id, asana_id in gh_and_asana_ids
        ]
        return self.bulk_insert_items_in_batches(OBJECTS_TABLE, items)

    # USERS TABLE

    def bulk_insert_github_handle_to_asana_user_id_mapping(
        self, gh_and_asana_ids: List[Tuple[str, str]]
    ):
        """Insert multiple mappings from github handle to Asana user ids.
        """
        items = [
            {
                self.GITHUB_HANDLE_KEY: {"S": gh_handle},
                self.USER_ID_KEY: {"S": asana_user_id},
            }
            for gh_handle, asana_user_id in gh_and_asana_ids
        ]
        return self.bulk_insert_items_in_batches(USERS_TABLE, items)

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
            TableName=USERS_TABLE,
            Key={self.GITHUB_HANDLE_KEY: {"S": github_handle.lower()}},
        )
        if "Item" in response:
            return response["Item"][self.USER_ID_KEY]["S"]
        else:
            return None

    def get_all_user_items(self) -> Iterator[DynamoDbUserItem]:
        """
            Get all DynamoDb items from the USERS_TABLE
        """
        response = self.client.scan(TableName=USERS_TABLE)
        yield from response["Items"]

        # May need to paginate, if the first page of data is > 1MB
        # (https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Scan.html#Scan.Pagination)
        while response.get("LastEvaluatedKey"):
            response = self.client.scan(
                TableName=USERS_TABLE, ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            yield from response["Items"]

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


def get_asana_id_from_two_github_node_ids(gh_node_id_a: str, gh_node_id_b: str) -> Optional[str]:
    """
        Using the singleton instance of DynamoDbClient, creating it if necessary:

        Retrieves the Asana object-id associated with the specified GitHub node-ids,
        or None, if no such association exists. Object-table associations are created
        by SGTM via the insert_github_node_to_asana_id_mapping method, below.
    """
    return DynamoDbClient.singleton().get_asana_id_from_github_node_id(
        _get_dynamodb_key_from_two_github_nodes(gh_node_id_a, gh_node_id_b)
    )


def insert_two_github_node_to_asana_id_mapping(gh_node_id_a: str, gh_node_id_b: str, asana_id: str):
    """
        Using the singleton instance of DynamoDbClient, creating it if necessary:

        Creates an association between two GitHub node-ids and an Asana object-id. The dynamoDb
        key is formed by concatenating the two GitHub node ids using a "-" separator.
    """
    dynamo_db_key = _get_dynamodb_key_from_two_github_nodes(gh_node_id_a, gh_node_id_b)
    print(f"Inserting key {dynamo_db_key} to DynamoDb.")
    return DynamoDbClient.singleton().insert_github_node_to_asana_id_mapping(
        _get_dynamodb_key_from_two_github_nodes(gh_node_id_a, gh_node_id_b), asana_id
    )


def get_all_user_items() -> List[dict]:
    return DynamoDbClient.singleton().get_all_user_items()


def bulk_insert_github_node_to_asana_id_mapping(
    gh_and_asana_ids: List[Tuple[str, str]]
):
    """
        Insert multiple mappings from github node ids to Asana object ids.
        Equivalent to calling insert_github_node_to_asana_id_mapping
        repeatedly, but in a single request.
    """
    DynamoDbClient.singleton().bulk_insert_github_node_to_asana_id_mapping(
        gh_and_asana_ids
    )


def bulk_insert_github_handle_to_asana_user_id_mapping(
    gh_and_asana_ids: List[Tuple[str, str]]
):
    """
        Insert multiple mappings from github handle to Asana user ids.
    """
    DynamoDbClient.singleton().bulk_insert_github_handle_to_asana_user_id_mapping(
        gh_and_asana_ids
    )

def _get_dynamodb_key_from_two_github_nodes(gh_node_id_a: str, gh_node_id_b: str) -> str:
    return f"{gh_node_id_a}-{gh_node_id_b}"
