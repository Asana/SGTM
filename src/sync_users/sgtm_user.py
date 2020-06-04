"""
Class representing a "User" for SGTM, which comprises of a Github handle and an
Asana domain user id. In practice, these should be actual developers in your
organization that are contributing to your repository, which have an Asana
account and a Github account.
"""
from __future__ import annotations
from typing import Any, List, Optional
from src.dynamodb.client import DynamoDbClient


class SgtmUser(object):
    # TODO: These should be configurable probably
    GITHUB_HANDLE_CUSTOM_FIELD_NAME = "Github Username"
    USER_ID_CUSTOM_FIELD_NAME = "user_id"

    def __init__(self, github_handle: str, domain_user_id: str):
        self.github_handle = github_handle

        # always lower-case github handles
        if self.github_handle:
            self.github_handle = self.github_handle.lower()

        self.domain_user_id = domain_user_id

    @classmethod
    def from_dynamodb_item(cls, item: dict) -> SgtmUser:
        return cls(
            item.get(DynamoDbClient.GITHUB_HANDLE_KEY, {}).get("S", ""),
            item.get(DynamoDbClient.USER_ID_KEY, {}).get("S", ""),
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
    def from_custom_fields_list(
        cls, custom_fields_list: List[dict]
    ) -> Optional[SgtmUser]:
        github_handle = None
        asana_user_id = None
        for cf in custom_fields_list:
            if cf["name"] == cls.USER_ID_CUSTOM_FIELD_NAME:
                asana_user_id = str(cls._get_custom_field_value(cf))
            elif cf["name"] == cls.GITHUB_HANDLE_CUSTOM_FIELD_NAME:
                github_handle = cls._get_custom_field_value(cf)

        if github_handle and asana_user_id:
            return cls(github_handle, asana_user_id)
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

    def __hash__(self) -> int:
        return hash(self.github_handle) ^ hash(self.domain_user_id)
