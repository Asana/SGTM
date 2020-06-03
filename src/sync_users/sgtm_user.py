from typing import Optional
from src.dynamodb.client import GITHUB_HANDLE_KEY, USER_ID_KEY


class SgtmUser(object):
    def __init__(self, github_handle: Optional[str], domain_user_id: str):
        # always lower-case github handles
        self.github_handle = github_handle.lower()

        # always lower-case github handles
        if self.github_handle:
            self.github_handle = self.github_handle.lower()

        self.domain_user_id = domain_user_id

    @classmethod
    def from_dynamodb_item(klass, item: dict) -> SgtmUser:
        return klass(item[GITHUB_HANDLE_KEY], item[USER_ID_KEY])

    def __eq__(self, other: SgtmUser) -> bool:
        return (self.github_handle == other.github_handle) and (
            self.domain_user_id == other.domain_user_id
        )

    def __ne__(self, other: SgtmUser) -> bool:
        return not self.__eq__(other)
