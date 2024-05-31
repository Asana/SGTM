from unittest.mock import patch, MagicMock
from python_dynamodb_lock.python_dynamodb_lock import DynamoDBLockError  # type: ignore

from src.dynamodb.lock import lock_client
from src.github import webhook
from src.github.models import PullRequest, PullRequestReviewComment, Review
from test.impl.mock_dynamodb_test_case import MockDynamoDbTestCase


class TestHandleGithubWebhook(MockDynamoDbTestCase):
    def test_handle_github_webhook_501_error_for_unknown_event_type(self):
        response = webhook.handle_github_webhook("unknown_event_type", {})

        self.assertEqual(response.status_code, "501")

    def test_swallow_dynamodb_lock_errors(self):
        response = None
        with lock_client.acquire_lock(
            "pull_request_1",
            sort_key="pull_request_1",
        ):
            with patch.object(lock_client, "acquire_lock") as acquire_lock:
                acquire_lock.side_effect = DynamoDBLockError("error")
                response = webhook.handle_github_webhook(
                    "pull_request", {"pull_request": {"node_id": "pull_request_1"}}
                )

        self.assertEqual(response.status_code, "500")


class HandleIssueCommentWebhook(MockDynamoDbTestCase):
    COMMENT_NODE_ID = "hijkl"
    ISSUE_NODE_ID = "ksjklsdf"

    def setUp(self):
        self.payload = {
            "action": "edited",
            "comment": {
                "node_id": self.COMMENT_NODE_ID,
            },
            "issue": {
                "node_id": self.ISSUE_NODE_ID,
            },
        }

    def test_handle_unknown_action_for_issue_comment(self):
        self.payload["action"] = "erroneous_action"

        response = webhook._handle_issue_comment_webhook(self.payload)
        self.assertEqual(response.status_code, "400")


@patch("src.github.controller.delete_comment")
@patch("src.github.controller.upsert_review")
class TestHandlePullRequestReviewComment(MockDynamoDbTestCase):
    PULL_REQUEST_REVIEW_ID = "123456"
    COMMENT_NODE_ID = "hijkl"
    PULL_REQUEST_NODE_ID = "abcde"

    def setUp(self):
        self.payload = {
            "pull_request": {"node_id": self.PULL_REQUEST_NODE_ID},
            "action": "edited",
            "comment": {
                "node_id": self.COMMENT_NODE_ID,
                "pull_request_review_id": self.PULL_REQUEST_REVIEW_ID,
            },
        }

    @patch.object(Review, "from_comment")
    @patch("src.github.graphql.client.get_pull_request_and_comment")
    def test_comment_edit(
        self,
        get_pull_request_and_comment,
        review_from_comment,
        upsert_review,
        delete_comment,
    ):
        self.payload["action"] = "edited"
        pull_request, comment = (
            MagicMock(spec=PullRequest),
            MagicMock(spec=PullRequestReviewComment),
        )
        review = MagicMock(spec=Review)
        get_pull_request_and_comment.return_value = pull_request, comment
        review_from_comment.return_value = review

        webhook._handle_pull_request_review_comment(self.payload)

        get_pull_request_and_comment.assert_called_once_with(
            self.PULL_REQUEST_NODE_ID, self.COMMENT_NODE_ID
        )
        upsert_review.assert_called_once_with(pull_request, review)
        review_from_comment.assert_called_once_with(comment)
        delete_comment.assert_not_called()

    @patch("src.github.graphql.client.get_pull_request")
    @patch("src.github.graphql.client.get_review_for_database_id")
    def test_comment_deletion_when_review_still_present(
        self,
        get_review_for_database_id,
        get_pull_request,
        upsert_review,
        delete_comment,
    ):
        self.payload["action"] = "deleted"

        pull_request = MagicMock(spec=PullRequest)
        review = MagicMock(spec=Review)
        get_pull_request.return_value = pull_request
        get_review_for_database_id.return_value = review

        webhook._handle_pull_request_review_comment(self.payload)

        get_pull_request.assert_called_once_with(self.PULL_REQUEST_NODE_ID)
        upsert_review.assert_called_once_with(pull_request, review)
        get_review_for_database_id.assert_called_once_with(
            self.PULL_REQUEST_NODE_ID, self.PULL_REQUEST_REVIEW_ID
        )
        delete_comment.assert_not_called()

    @patch("src.github.controller.upsert_pull_request")
    @patch("src.github.graphql.client.get_review_for_database_id", return_value=None)
    def test_comment_deletion_when_review_not_found(
        self,
        get_review_for_database_id,
        upsert_pull_request,
        upsert_review,
        delete_comment,
    ):
        self.payload["action"] = "deleted"

        webhook._handle_pull_request_review_comment(self.payload)

        upsert_review.assert_not_called()
        get_review_for_database_id.assert_called_once_with(
            self.PULL_REQUEST_NODE_ID, self.PULL_REQUEST_REVIEW_ID
        )
        delete_comment.assert_called_once_with(self.COMMENT_NODE_ID)


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
