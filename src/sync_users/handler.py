from src.asana import client as asana_client
from src.config import USERS_TABLE, ASANA_USERS_PROJECT_ID
from src.dynamodb import client as dynamodb_client
from src.logger import logger
from src.sync_users.sgtm_user import SgtmUser


def handler(event: dict, context: dict) -> None:
    """
        Entrypoint for Lambda function that syncs the mapping of Github handles
        to Asana user ids with the dynamodb table USERS_TABLE. This happens
        through an Asana project with custom fields - one task per user with
        custom fields defined in SgtmUser (GITHUB_HANDLE_CUSTOM_FIELD_NAME,
        USER_ID_CUSTOM_FIELD_NAME)

        `event` and `context` are passed into the Lambda function, but we don't
        really care what they are for this function, and they are ignored
    """
    logger.info(
        "Starting sync from Asana project to Dynamodb {} table".format(USERS_TABLE)
    )

    users_in_dynamodb = set(
        [
            SgtmUser.from_dynamodb_item(item)
            for item in dynamodb_client.get_all_user_items()
        ]
    )
    logger.info("Found {} users in dynamodb".format(len(users_in_dynamodb)))

    asana_user_tasks_from_asana_project = asana_client.find_all_tasks_for_project(
        ASANA_USERS_PROJECT_ID, opt_fields=["custom_fields"]
    )
    users_in_asana = [
        u
        for u in [
            SgtmUser.from_custom_fields_list(task["custom_fields"])
            for task in asana_user_tasks_from_asana_project
        ]
        if u is not None
    ]
    logger.info("Found {} users in Asana".format(len(users_in_asana)))

    users_to_add = [user for user in users_in_asana if user not in users_in_dynamodb]
    logger.info("{} users to add to DynamoDb".format(len(users_to_add)))

    # Batch write the users
    if len(users_to_add) > 0:
        dynamodb_client.bulk_insert_github_handle_to_asana_user_id_mapping(
            [(u.github_handle, u.domain_user_id) for u in users_to_add]
        )
        logger.info("Done writing user mappings to DynamoDb")
