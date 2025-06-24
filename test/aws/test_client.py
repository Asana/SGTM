import src.aws.dynamodb_client as dynamodb_client
from test.impl.mock_dynamodb_test_case import MockDynamoDbTestCase


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

    def test_attachment_operations(self):
        gh_node_id = "test-pr-123"
        asana_id = "task-456"

        # First, test getting attachments when none exist
        attachments = dynamodb_client.get_attachments_for_github_node(gh_node_id)
        self.assertEqual(attachments, {})

        # Create initial mapping
        dynamodb_client.insert_github_node_to_asana_id_mapping(gh_node_id, asana_id)

        # Test existing entry behavior: entry exists but has no attachments field
        # This simulates existing production entries that were created before attachment feature
        attachments = dynamodb_client.get_attachments_for_github_node(gh_node_id)
        self.assertEqual(attachments, {})  # Should return empty dict, not error

        # Add some attachments
        test_attachments = {
            "asset-123": "asana-attachment-456",
            "asset-789": "asana-attachment-101",
            "https://example.com/image.png": "asana-attachment-999",
        }
        dynamodb_client.update_attachments_for_github_node(gh_node_id, test_attachments)

        # Verify attachments were stored correctly
        retrieved_attachments = dynamodb_client.get_attachments_for_github_node(
            gh_node_id
        )
        self.assertEqual(retrieved_attachments, test_attachments)

        # Verify the asana-id is still preserved
        self.assertEqual(
            dynamodb_client.get_asana_id_from_github_node_id(gh_node_id), asana_id
        )

        # Update attachments (remove one, add one, keep one)
        updated_attachments = {
            "asset-789": "asana-attachment-101",  # kept
            "asset-new": "asana-attachment-222"  # added
            # asset-123 and https://example.com/image.png removed
        }
        dynamodb_client.update_attachments_for_github_node(
            gh_node_id, updated_attachments
        )

        # Verify the update worked
        retrieved_attachments = dynamodb_client.get_attachments_for_github_node(
            gh_node_id
        )
        self.assertEqual(retrieved_attachments, updated_attachments)

        # Verify asana-id is still preserved after update
        self.assertEqual(
            dynamodb_client.get_asana_id_from_github_node_id(gh_node_id), asana_id
        )

        # Test updating attachments for a node that doesn't exist yet
        new_gh_node_id = "new-pr-999"
        new_attachments = {"new-asset": "new-asana-attachment"}
        dynamodb_client.update_attachments_for_github_node(
            new_gh_node_id, new_attachments
        )

        # Should create the record with just the attachments (no asana-id)
        retrieved_attachments = dynamodb_client.get_attachments_for_github_node(
            new_gh_node_id
        )
        self.assertEqual(retrieved_attachments, new_attachments)

        # But asana-id should be None since we never set it
        self.assertEqual(
            dynamodb_client.get_asana_id_from_github_node_id(new_gh_node_id), None
        )


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
