from src.dynamodb import client as _inner_dynamodb_client


github_users = {
    "github_assignee_login": "ASSIGNEE_ASANA_DOMAIN_USER_ID",
    "github_assignee_login_annie": "ANNIE_ASANA_DOMAIN_USER_ID",
    "github_assignee_login_billy": "BILLY_ASANA_DOMAIN_USER_ID",
    "github_author_login": "AUTHOR_ASANA_DOMAIN_USER_ID",
    "github_reviewer_login": "REVIEWER_ASANA_DOMAIN_USER_ID",
    "github_commentor_login": "COMMENTOR_ASANA_DOMAIN_USER_ID",
    "github_requested_reviewer_login": "REQUESTED_REVIEWER_ASANA_DOMAIN_USER_ID",
    "github_at_mentioned_login": "AT_MENTIONED_ASANA_DOMAIN_USER_ID"
}


class DynamoDbClient:

    @classmethod
    def initialize(cls):
        _inner_dynamodb_client.get_asana_domain_user_id_from_github_handle = cls.get_asana_domain_user_id_from_github_handle

    @staticmethod
    def get_asana_domain_user_id_from_github_handle(github_handle):
        return github_users.get(github_handle, None)
