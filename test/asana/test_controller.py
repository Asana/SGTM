from unittest.mock import patch, Mock, MagicMock, call


from test.impl.base_test_case_class import BaseClass

from src.github.models import Review, Comment
from src.asana import controller


@patch.object(controller, 'asana_helpers')
@patch('src.asana.client.add_comment')
@patch('src.dynamodb.client.insert_github_node_to_asana_id_mapping')
class TestUpsertGithubReviewToTask(BaseClass):
    REVIEW_ID = "12345"
    ASANA_COMMENT_ID = "56789"
    ASANA_TASK_ID = "abcde"
    ASANA_COMMENT_BODY = "<body>Here's a comment</body>"

    def _mock_comment(self, id):
        return MagicMock(spec=Comment, id=MagicMock(return_value=id))

    def _mock_review(self, id, comments=[]):
        return MagicMock(spec=Review, id=MagicMock(return_value=id), comments=MagicMock(return_value=comments))

    @patch('src.dynamodb.client.get_asana_id_from_github_node_id', return_value=None)
    def test_created_review_with_no_comments(self, get_asana_id_from_github_node_id, insert_github_node_to_asana_id_mapping, add_comment, asana_helpers):
        review = self._mock_review(self.REVIEW_ID)
        asana_helpers.asana_comment_from_github_review.return_value = self.ASANA_COMMENT_BODY

        add_comment.return_value = self.ASANA_COMMENT_ID

        controller.upsert_github_review_to_task(review, self.ASANA_TASK_ID)

        add_comment.assert_called_once_with(self.ASANA_TASK_ID, self.ASANA_COMMENT_BODY)
        asana_helpers.asana_comment_from_github_review.assert_called_once_with(review)
        insert_github_node_to_asana_id_mapping.assert_called_once_with(self.REVIEW_ID, self.ASANA_COMMENT_ID)
        get_asana_id_from_github_node_id.assert_called_once_with(self.REVIEW_ID)

    @patch('src.dynamodb.client.get_asana_id_from_github_node_id', return_value=None)
    def test_created_review_with_comments(self, get_asana_id_from_github_node_id, insert_github_node_to_asana_id_mapping, add_comment, asana_helpers):
        review = self._mock_review(self.REVIEW_ID, [self._mock_comment("123"), self._mock_comment("456")])
        asana_helpers.asana_comment_from_github_review.return_value = self.ASANA_COMMENT_BODY

        add_comment.return_value = self.ASANA_COMMENT_ID

        controller.upsert_github_review_to_task(review, self.ASANA_TASK_ID)

        insert_github_node_to_asana_id_mapping.assert_has_calls([
            call(self.REVIEW_ID, self.ASANA_COMMENT_ID),
            call("123", self.ASANA_COMMENT_ID),
            call("456", self.ASANA_COMMENT_ID)
        ], any_order=True)
        add_comment.assert_called_once_with(self.ASANA_TASK_ID, self.ASANA_COMMENT_BODY)
        get_asana_id_from_github_node_id.assert_called_once_with(self.REVIEW_ID)


@patch.object(controller, 'asana_client')
class TestMocks(BaseClass):
    def test_something(self, mock_client):
        assert True


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
