"""
Test case that should be used for tests that require integration with dynamodb
or other external resources.
"""
from src.config import USERS_TABLE


class MockDynamoDbTestDataHelper(object):
    def __init__(self, client):
        self.client = client

    def insert_user_into_user_table(self, gh_handle: str, asana_domain_user_id: str):
        self.client.put_item(
            TableName=USERS_TABLE,
            Item={
                "github/handle": {"S": gh_handle.lower()},
                "asana/domain-user-id": {"S": asana_domain_user_id},
            },
        )
