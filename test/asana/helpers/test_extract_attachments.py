from src.asana import helpers as asana_helpers
from test.impl.base_test_case_class import BaseClass
from unittest.mock import patch, MagicMock, mock_open


class TestExtractAttachments(BaseClass):
    def test_extract_no_attachments(self):
        github_html = 'No urls here!! <img alt="but some weird formatting" /> (oops)'
        attachments = asana_helpers._extract_attachments(github_html)
        self.assertEqual(len(attachments), 0)

    def test_extract_attachment_with_unknown_extension(self):
        github_html = 'Ok here it is <img src="www.photopng.com/this.fakeg" alt="photoo ooo" /> and there it was'
        attachments = asana_helpers._extract_attachments(github_html)
        self.assertEqual(len(attachments), 0)

    def test_extract_attachments_with_extensions(self):
        github_html = (
            'Ok here\'s the first: <img src="www.photopng.com/this.png" alt="photo" /> and the'
            ' second!! <img src="giphy.com/example.gif" alt="giferino" />'
        )
        attachments = asana_helpers._extract_attachments(github_html)
        self.assertListEqual(
            attachments,
            [
                asana_helpers.AttachmentData(
                    file_name="photo.png",
                    file_url="www.photopng.com/this.png",
                    file_type="image/png",
                    original_asset_id="www.photopng.com/this.png",
                ),
                asana_helpers.AttachmentData(
                    file_name="giferino.gif",
                    file_url="giphy.com/example.gif",
                    file_type="image/gif",
                    original_asset_id="giphy.com/example.gif",
                ),
            ],
        )

    def test_extract_attachments_with_double_extensions(self):
        github_html = (
            'Ok here\'s the first: <img src="www.photopng.com/this.png/this-small.png" alt="photo" /> and the'
            ' second!! <img src="giphy.com/cute-cat.jpg/small.jpg" alt="cute-cat" />'
            ' third! <img src="giphy.com/even-cuter-cat.jpg/small.jpg" alt="even-cuter-cat" />'
        )
        attachments = asana_helpers._extract_attachments(github_html)
        self.assertListEqual(
            attachments,
            [
                asana_helpers.AttachmentData(
                    file_name="photo.png",
                    file_url="www.photopng.com/this.png/this-small.png",
                    file_type="image/png",
                    original_asset_id="www.photopng.com/this.png/this-small.png",
                ),
                asana_helpers.AttachmentData(
                    file_name="cute-cat.jpg",
                    file_url="giphy.com/cute-cat.jpg/small.jpg",
                    file_type="image/jpeg",
                    original_asset_id="giphy.com/cute-cat.jpg/small.jpg",
                ),
                asana_helpers.AttachmentData(
                    file_name="even-cuter-cat.jpg",
                    file_url="giphy.com/even-cuter-cat.jpg/small.jpg",
                    file_type="image/jpeg",
                    original_asset_id="giphy.com/even-cuter-cat.jpg/small.jpg",
                ),
            ],
        )

    def test_extract_attachment_with_github_asset_url(self):
        github_html = 'Ok here\'s the first: <img src="https://api.github.com/assets/long-unique-uuid.png?token=123321" alt="github-asset" /> and that\'s it!'
        attachments = asana_helpers._extract_attachments(github_html)
        self.assertListEqual(
            attachments,
            [
                asana_helpers.AttachmentData(
                    file_name="github-asset.png",
                    file_url="https://api.github.com/assets/long-unique-uuid.png?token=123321",
                    file_type="image/png",
                    original_asset_id="long-unique-uuid",
                ),
            ],
        )

    def test_extract_attachment_with_github_img_tag_url(self):
        github_html = (
            'For some reason, github also has img tags like this: <img width="745" alt="Screenshot 2025-04-22 at 19 43 43" src="https://api.github.com/assets/long-unique-uuid.png?token=123321" />'
            "inside markdown comments. This should not be a problem for us."
        )
        attachments = asana_helpers._extract_attachments(github_html)
        self.assertListEqual(
            attachments,
            [
                asana_helpers.AttachmentData(
                    file_name="Screenshot 2025-04-22 at 19 43 43.png",
                    file_url="https://api.github.com/assets/long-unique-uuid.png?token=123321",
                    file_type="image/png",
                    original_asset_id="long-unique-uuid",
                ),
            ],
        )

    def test_extract_attachment_with_github_video_url(self):
        github_html = "Ok here's the first: <video src=\"https://api.github.com/assets/long-unique-uuid.mov?token=123321\" /> and that's it!"
        attachments = asana_helpers._extract_attachments(github_html)
        self.assertListEqual(
            attachments,
            [
                asana_helpers.AttachmentData(
                    file_name="long-unique-uuid.mov",
                    file_url="https://api.github.com/assets/long-unique-uuid.mov?token=123321",
                    file_type="video/mov",
                    original_asset_id="long-unique-uuid",
                ),
            ],
        )

    def test_extract_attachment_without_extension(self):
        github_html = 'Ok here\'s the first: <img src="www.photopng.com/this.png" alt="photo" /> and that\'s it!'
        attachments = asana_helpers._extract_attachments(github_html)
        self.assertListEqual(
            attachments,
            [
                asana_helpers.AttachmentData(
                    file_name="photo.png",
                    file_url="www.photopng.com/this.png",
                    file_type="image/png",
                    original_asset_id="www.photopng.com/this.png",
                ),
            ],
        )

    def test_extract_attachment_no_file_name_given(self):
        github_html = 'Ok here\'s the first: <img src="www.photopng.com/this.png" alt="" /> and that\'s it!'
        attachments = asana_helpers._extract_attachments(github_html)
        self.assertListEqual(
            attachments,
            [
                asana_helpers.AttachmentData(
                    file_name="this.png",
                    file_url="www.photopng.com/this.png",
                    file_type="image/png",
                    original_asset_id="www.photopng.com/this.png",
                ),
            ],
        )


class TestSyncAttachments(BaseClass):
    @patch("src.asana.helpers.dynamodb_client")
    @patch("src.asana.helpers.asana_client")
    @patch("urllib.request.urlopen")
    def test_sync_attachments_delete_keep_create(
        self, mock_urlopen, mock_asana_client, mock_dynamodb_client
    ):
        """Test that sync_attachments correctly deletes, keeps, and creates attachments"""

        # Setup test data
        body_html = """
        <img src="asset-2.png" alt="kept" />
        <img src="asset-3.png" alt="new" />
        """
        task_id = "task-123"
        github_node_id = "pr-456"

        # Mock existing attachments in DynamoDB
        existing_attachments = {
            "asset-1.png": "asana-attach-1",  # Will be deleted
            "asset-2.png": "asana-attach-2",  # Will be kept
        }
        mock_dynamodb_client.get_attachments_for_github_node.return_value = (
            existing_attachments
        )

        # Mock file download
        mock_file = MagicMock()
        mock_file.read.return_value = b"fake file content"
        mock_urlopen.return_value.__enter__.return_value = mock_file

        # Mock Asana client
        mock_asana_client.create_attachment_on_task.return_value = "asana-attach-3"

        # Call the function
        asana_helpers.sync_attachments(body_html, task_id, github_node_id)

        # Verify deletion
        mock_asana_client.delete_attachment.assert_called_once_with("asana-attach-1")

        # Verify creation
        mock_asana_client.create_attachment_on_task.assert_called_once_with(
            task_id, b"fake file content", "new.png", "image/png"
        )

        # Verify DynamoDB update - this is the key test for the bug fix
        expected_new_attachments = {
            "asset-2.png": "asana-attach-2",  # Kept from existing
            "asset-3.png": "asana-attach-3",  # Newly created
            # asset-1.png should NOT be here (this was the bug)
        }
        mock_dynamodb_client.update_attachments_for_github_node.assert_called_once_with(
            github_node_id, expected_new_attachments
        )

    @patch("src.asana.helpers.dynamodb_client")
    @patch("src.asana.helpers.asana_client")
    def test_sync_attachments_no_changes(self, mock_asana_client, mock_dynamodb_client):
        """Test that sync_attachments handles no changes correctly"""

        body_html = '<img src="asset-1.png" alt="existing" />'
        task_id = "task-123"
        github_node_id = "pr-456"

        # Mock existing attachments - same as current
        existing_attachments = {"asset-1.png": "asana-attach-1"}
        mock_dynamodb_client.get_attachments_for_github_node.return_value = (
            existing_attachments
        )

        # Call the function
        asana_helpers.sync_attachments(body_html, task_id, github_node_id)

        # Verify no Asana operations
        mock_asana_client.delete_attachment.assert_not_called()
        mock_asana_client.create_attachment_on_task.assert_not_called()

        # Verify DynamoDB update with same data
        mock_dynamodb_client.update_attachments_for_github_node.assert_called_once_with(
            github_node_id, existing_attachments
        )

    @patch("src.asana.helpers.dynamodb_client")
    @patch("src.asana.helpers.asana_client")
    def test_sync_attachments_empty_content(
        self, mock_asana_client, mock_dynamodb_client
    ):
        """Test that sync_attachments deletes all attachments when content is empty"""

        body_html = "No attachments here!"
        task_id = "task-123"
        github_node_id = "pr-456"

        # Mock existing attachments
        existing_attachments = {
            "asset-1.png": "asana-attach-1",
            "asset-2.png": "asana-attach-2",
        }
        mock_dynamodb_client.get_attachments_for_github_node.return_value = (
            existing_attachments
        )

        # Call the function
        asana_helpers.sync_attachments(body_html, task_id, github_node_id)

        # Verify all attachments deleted
        self.assertEqual(mock_asana_client.delete_attachment.call_count, 2)
        mock_asana_client.delete_attachment.assert_any_call("asana-attach-1")
        mock_asana_client.delete_attachment.assert_any_call("asana-attach-2")

        # Verify no creation
        mock_asana_client.create_attachment_on_task.assert_not_called()

        # Verify DynamoDB updated with empty dict
        mock_dynamodb_client.update_attachments_for_github_node.assert_called_once_with(
            github_node_id, {}
        )


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
