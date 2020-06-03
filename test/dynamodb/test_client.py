from test.impl.mock_dynamodb_test_case import MockDynamoDbTestCase
import src.dynamodb.client as dynamodb_client


class DynamodbClientTest(MockDynamoDbTestCase):
    def test_get_asana_id_from_github_node_id_and_insert_github_node_to_asana_id_mapping(
        self,
    ):
        gh_node_id = "abcdefg"
        asana_id = "123456"

        # First, no mapping exists
        self.assertEqual(
            dynamodb_client.get_asana_id_from_github_node_id(gh_node_id), None
        )
        # Then, add the mapping
        dynamodb_client.insert_github_node_to_asana_id_mapping(gh_node_id, asana_id)
        # Now we get the asana_id
        self.assertEqual(
            dynamodb_client.get_asana_id_from_github_node_id(gh_node_id), asana_id
        )

    def test_get_asana_domain_user_id_from_github_handle(self):
        gh_handle = "Elaine Benes"
        asana_user_id = "12345"
        self.test_data.insert_user_into_user_table(gh_handle, asana_user_id)
        self.assertEqual(
            dynamodb_client.get_asana_domain_user_id_from_github_handle(gh_handle),
            asana_user_id,
        )

    def test_bulk_insert_github_handle_to_asana_user_id_mapping(self):
        mappings = [("user1", "1"), ("user2", "2")]
        dynamodb_client.bulk_insert_github_handle_to_asana_user_id_mapping(mappings)
        self.assertEqual(
            dynamodb_client.get_asana_domain_user_id_from_github_handle("user1"), "1",
        )
        self.assertEqual(
            dynamodb_client.get_asana_domain_user_id_from_github_handle("user2"), "2",
        )
        user_items = dynamodb_client.get_all_user_items()
        self.assertEqual(len(user_items), 2)


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
