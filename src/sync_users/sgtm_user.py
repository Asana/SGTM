from __future__ import annotations
from typing import Any, List, Optional
from src.dynamodb.client import DynamoDbClient


class SgtmUser(object):
    # TODO: These should be configurable probably
    GITHUB_HANDLE_CUSTOM_FIELD_NAME = "Github Username"
    USER_ID_CUSTOM_FIELD_NAME = "user_id"

    def __init__(self, github_handle: Optional[str], domain_user_id: str):
        # always lower-case github handles
        self.github_handle = github_handle.lower()

        # always lower-case github handles
        if self.github_handle:
            self.github_handle = self.github_handle.lower()

        self.domain_user_id = domain_user_id

    @classmethod
    def from_dynamodb_item(klass, item: dict) -> SgtmUser:
        return klass(
            item[DynamoDbClient.GITHUB_HANDLE_KEY]["S"],
            item[DynamoDbClient.USER_ID_KEY]["S"],
        )

    @staticmethod
    def _get_custom_field_value(custom_field: dict):
        if custom_field["type"] == "text":
            return custom_field["text_value"]
        elif custom_field["type"] == "number":
            return custom_field["number_value"]
        elif custom_field["type"] == "enum":
            return custom_field["enum_value"]
        else:
            raise Exception(
                "Unknown custom field type: {}".format(custom_field["type"])
            )

    @classmethod
    def from_custom_fields_list(klass, custom_fields_list: List[dict]) -> SgtmUser:
        github_handle = None
        asana_user_id = None
        for cf in custom_fields_list:
            if cf["name"] == klass.USER_ID_CUSTOM_FIELD_NAME:
                asana_user_id = str(klass._get_custom_field_value(cf))
            elif cf["name"] == klass.GITHUB_HANDLE_CUSTOM_FIELD_NAME:
                github_handle = klass._get_custom_field_value(cf)

        if github_handle is not None and asana_user_id is not None:
            return klass(github_handle, asana_user_id)
        else:
            return None

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, SgtmUser):
            return (self.github_handle == other.github_handle) and (
                self.domain_user_id == other.domain_user_id
            )
        return False

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)
