from unittest.mock import patch, Mock, MagicMock

from test.impl.base_test_case_class import BaseClass

from src.github import webhook
from src.github.models import PullRequest, PullRequestReviewComment, Review

@patch.object(webhook, 'dynamodb_lock')
class TestHandlePullRequestReviewComment(BaseClass):

    def test_stuff(self, mock_lock):

        # from src.dynamodb.lock import dynamodb_lock
        # with dynamodb_lock():
            # x = "Hi!"
        assert True

    @patch.object(Review, 'from_comment')
    @patch('src.github.controller.upsert_review')
    @patch('src.github.graphql.client.get_pull_request_and_comment')
    def test_more_stuff(self, get_pull_request_and_comment, upsert_review, review_from_comment, lock):
        payload = {
            "pull_request": {
                "node_id": "abcde"
            },
            "action": "edited",
            "comment": {
                "node_id": "hijkl",
                "pull_request_review_id": "1234566"
            }

        }
        # print(f"1: {get_pull_request_and_comment}")
        # print(f"2: {upsert_review}")
        # print(f"3: {lock}")
        pull_request, comment = MagicMock(spec=PullRequest), MagicMock(spec=PullRequestReviewComment)
        review = MagicMock(spec=Review)
        get_pull_request_and_comment.return_value = pull_request, comment
        review_from_comment.return_value = review

        webhook._handle_pull_request_review_comment(payload)

        get_pull_request_and_comment.assert_called_once_with("abcde", "hijkl")
        upsert_review.assert_called_once_with(pull_request, review)
        review_from_comment.assert_called_once_with(comment)

if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
