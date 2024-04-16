from unittest.mock import patch
from test.impl.mock_dynamodb_test_case import MockDynamoDbTestCase
import src.dynamodb.client as dynamodb_client
from test.test_utils import magic_mock_with_return_type_value


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


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
