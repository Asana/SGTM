import boto3  # type: ignore
from typing import TypedDict, List, Optional, Tuple

from src.config import OBJECTS_TABLE, AWS_REGION
from src.logger import logger


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
            logger.warning(
                f"Asana id not found in dynamodb for github node id {gh_node_id}"
            )
            return None

    def insert_github_node_to_asana_id_mapping(self, gh_node_id: str, asana_id: str):
        """
        Creates an association between a GitHub node-id and an Asana object-id
        """
        response = self.client.put_item(
            TableName=OBJECTS_TABLE,
            Item={"github-node": {"S": gh_node_id}, "asana-id": {"S": asana_id}},
        )
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            logger.info(f"Inserted into dynamodb {gh_node_id} -> {asana_id}")
        else:
            logger.warning(
                f"Error inserting into dynamodb {gh_node_id} -> {asana_id}, response {response}"
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

    @staticmethod
    def _create_client():
        return boto3.client("dynamodb", region_name=AWS_REGION)


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
