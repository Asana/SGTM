import src.dynamodb.client as dynamodb_client


class DynamoDbClient(object):

    def __init__(self):
        self.github_users = {
            "github_assignee_login": "ASSIGNEE_ASANA_DOMAIN_USER_ID",
            "github_assignee_login_annie": "ANNIE_ASANA_DOMAIN_USER_ID",
            "github_assignee_login_billy": "BILLY_ASANA_DOMAIN_USER_ID",
            "github_author_login": "AUTHOR_ASANA_DOMAIN_USER_ID",
            "github_reviewer_login": "REVIEWER_ASANA_DOMAIN_USER_ID",
            "github_commentor_login": "COMMENTOR_ASANA_DOMAIN_USER_ID",
            "github_requested_reviewer_login": "REQUESTED_REVIEWER_ASANA_DOMAIN_USER_ID",
            "github_at_mentioned_login": "AT_MENTIONED_ASANA_DOMAIN_USER_ID"
        }

    @classmethod
    def initialize(cls):
        dynamodb_client.inject(DynamoDbClient())

    @classmethod
    def finalize(cls):
        dynamodb_client.inject(None)

    def get_asana_domain_user_id_from_github_handle(self, github_handle):
        return self.github_users.get(github_handle, None)
