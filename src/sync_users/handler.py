from src.dynamodb import client as dynamodb_client
from src.config import USERS_TABLE, ASANA_USERS_PROJECT_ID
from src.logger import logger
from src.sync_users.sgtm_user import SgtmUser


def handler(event: dict, context: dict) -> None:
    logger.info(
        "Starting sync from Asana project to Dynamodb {} table".format(USERS_TABLE)
    )

    users_in_dynamodb = [
        SgtmUser.from_dynamodb_item(item)
        for item in dynamodb_client.get_all_user_items()
    ]
    logger.info("Found {} users in dynamodb".format(len(users_in_dynamodb)))

    asana_users_from_asana_project = asana_client.find_all_tasks_for_project(
        ASANA_USERS_PROJECT_ID, opt_fields=["custom_fields"]
    )
