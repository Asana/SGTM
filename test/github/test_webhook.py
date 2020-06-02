from unittest.mock import patch, Mock, MagicMock

from test.impl.base_test_case_class import BaseClass

from src.github import webhook
from src.github.models import PullRequest, PullRequestReviewComment, Review


@patch.object(webhook, "dynamodb_lock")
@patch("src.github.controller.delete_comment")
@patch("src.github.controller.upsert_review")
class TestHandlePullRequestReviewComment(BaseClass):
    @patch.object(Review, "from_comment")
    @patch("src.github.graphql.client.get_pull_request_and_comment")
    def test_comment_edit(
        self,
        get_pull_request_and_comment,
        review_from_comment,
        upsert_review,
        delete_comment,
        lock,
    ):
        payload = {
            "pull_request": {"node_id": "abcde"},
            "action": "edited",
            "comment": {"node_id": "hijkl", "pull_request_review_id": "1234566"},
        }
        pull_request, comment = (
            MagicMock(spec=PullRequest),
            MagicMock(spec=PullRequestReviewComment),
        )
        review = MagicMock(spec=Review)
        get_pull_request_and_comment.return_value = pull_request, comment
        review_from_comment.return_value = review

        webhook._handle_pull_request_review_comment(payload)

        get_pull_request_and_comment.assert_called_once_with("abcde", "hijkl")
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
        lock,
    ):
        payload = {
            "pull_request": {"node_id": "abcde"},
            "action": "deleted",
            "comment": {"node_id": "hijkl", "pull_request_review_id": "1234566"},
        }

        pull_request = MagicMock(spec=PullRequest)
        review = MagicMock(spec=Review)
        get_pull_request.return_value = pull_request
        get_review_for_database_id.return_value = review

        webhook._handle_pull_request_review_comment(payload)

        get_pull_request.assert_called_once_with("abcde")
        upsert_review.assert_called_once_with(pull_request, review)
        get_review_for_database_id.assert_called_once_with("abcde", "1234566")
        delete_comment.assert_not_called()

    @patch(
        "src.github.graphql.client.get_pull_request",
        return_value=MagicMock(spec=PullRequest),
    )
    @patch("src.github.graphql.client.get_review_for_database_id", return_value=None)
    def test_comment_deletion_when_review_not_found(
        self,
        get_review_for_database_id,
        get_pull_request,
        upsert_review,
        delete_comment,
        lock,
    ):
        payload = {
            "pull_request": {"node_id": "abcde"},
            "action": "deleted",
            "comment": {"node_id": "hijkl", "pull_request_review_id": "1234566"},
        }

        webhook._handle_pull_request_review_comment(payload)

        get_pull_request.assert_called_once_with("abcde")
        upsert_review.assert_not_called()
        get_review_for_database_id.assert_called_once_with("abcde", "1234566")
        delete_comment.assert_called_once_with("hijkl")


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
