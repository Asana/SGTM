from src.dynamodb import client as _inner_dynamodb_client


class DynamoDbClient:

    @classmethod
    def initialize(cls):
        _inner_dynamodb_client.get_asana_domain_user_id_from_github_handle = cls.get_asana_domain_user_id_from_github_handle


    @staticmethod
    def get_asana_domain_user_id_from_github_handle(github_handle):
        if github_handle == "GITHUB_ASSIGNEE_LOGIN":
            return "ASSIGNEE_ASANA_DOMAIN_USER_ID"
        elif github_handle == "GITHUB_ASSIGNEE_LOGIN_ANNIE":
            return "ANNIE_ASANA_DOMAIN_USER_ID"
        elif github_handle == "GITHUB_ASSIGNEE_LOGIN_BILLY":
            return "BILLY_ASANA_DOMAIN_USER_ID"
        elif github_handle == "GITHUB_AUTHOR_LOGIN":
            return "AUTHOR_ASANA_DOMAIN_USER_ID"
        return None
