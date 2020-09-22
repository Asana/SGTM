from unittest.mock import patch, Mock, MagicMock
from test.impl.base_test_case_class import BaseClass

from src.github import webhook
from src.github.models import PullRequest, PullRequestReviewComment, Review, Commit
from test.impl.mock_dynamodb_test_case import MockDynamoDbTestCase
from test.impl.builders import builder, build
import src.github.graphql.client as graphql_client
import src.github.controller as github_controller
import src.github.client as github_client
import src.dynamodb.client as dynamodb_client

@patch("os.getenv")
@patch.object(graphql_client, "get_pull_request_for_commit")
@patch.object(github_controller, "upsert_pull_request")
@patch.object(github_client, "merge_pull_request")
class GithubWebhookTest(MockDynamoDbTestCase):
    def test_handle_status_webhook_ready_for_automerge(
        self,
        merge_pull_request_mock,
        upsert_pull_request_mock,
        get_pull_request_for_commit_mock,
        get_env_mock,
    ):
        # set env variable to True to enable automerge
        get_env_mock.return_value = True

        # Creating a pull request that can be automerged
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_SUCCESSFUL))
            .review(
                builder.review().submitted_at("2020-01-13T14:59:58Z").state("APPROVED")
            )
            .mergeable(True)
            .title("blah blah [shipit]")
        )

        existing_task_id = uuid4().hex
        dynamodb_client.insert_github_node_to_asana_id_mapping(
            pull_request.id(), existing_task_id
        )

        get_pull_request_for_commit_mock.return_value = pull_request

        github_webhook.handle_github_webhook(
            "status", pull_request.commits()[0].to_raw()
        )

        upsert_pull_request_mock.assert_not_called()
        merge_pull_request_mock.assert_called_with(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            pull_request.number(),
            pull_request.title(),
            pull_request.body(),
        )

    def test_handle_status_webhook_not_ready_for_automerge(
        self,
        merge_pull_request_mock,
        upsert_pull_request_mock,
        get_pull_request_for_commit_mock,
        get_env_mock,
    ):
        # set env variable to True to enable automerge
        get_env_mock.return_value = True

        # Creating a pull request that can be automerged
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_FAILED))
            .review(
                builder.review().submitted_at("2020-01-13T14:59:58Z").state("APPROVED")
            )
            .mergeable(True)
            .title("blah blah [shipit]")
        )

        existing_task_id = uuid4().hex
        dynamodb_client.insert_github_node_to_asana_id_mapping(
            pull_request.id(), existing_task_id
        )

        get_pull_request_for_commit_mock.return_value = pull_request

        github_webhook.handle_github_webhook(
            "status", pull_request.commits()[0].to_raw()
        )

        upsert_pull_request_mock.assert_called_with(pull_request)
        merge_pull_request_mock.assert_not_called()

    def test_handle_status_webhook_ready_for_automerge(
        self,
        merge_pull_request_mock,
        upsert_pull_request_mock,
        get_pull_request_for_commit_mock,
        get_env_mock,
    ):
        # set env variable to False to disable automerge
        get_env_mock.return_value = False

        # Creating a pull request that can be automerged
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_SUCCESSFUL))
            .review(
                builder.review().submitted_at("2020-01-13T14:59:58Z").state("APPROVED")
            )
            .mergeable(True)
            .title("blah blah [shipit]")
        )

        existing_task_id = uuid4().hex
        dynamodb_client.insert_github_node_to_asana_id_mapping(
            pull_request.id(), existing_task_id
        )

        get_pull_request_for_commit_mock.return_value = pull_request

        github_webhook.handle_github_webhook(
            "status", pull_request.commits()[0].to_raw()
        )

        upsert_pull_request_mock.assert_called_with(pull_request)
        merge_pull_request_mock.assert_not_called()


class TestHandleGithubWebhook(BaseClass):
    def test_handle_github_webhook_501_error_for_unknown_event_type(self):
        response = webhook.handle_github_webhook("unknown_event_type", {})

        self.assertEqual(response.status_code, "501")


@patch.object(webhook, "dynamodb_lock")
class HandleIssueCommentWebhook(BaseClass):
    COMMENT_NODE_ID = "hijkl"
    ISSUE_NODE_ID = "ksjklsdf"

    def setUp(self):
        self.payload = {
            "action": "edited",
            "comment": {"node_id": self.COMMENT_NODE_ID,},
            "issue": {"node_id": self.ISSUE_NODE_ID,},
        }

    def test_handle_unknown_action_for_issue_comment(self, lock):
        self.payload["action"] = "erroneous_action"

        response = webhook._handle_issue_comment_webhook(self.payload)
        self.assertEqual(response.status_code, "400")


@patch.object(webhook, "dynamodb_lock")
@patch("src.github.controller.delete_comment")
@patch("src.github.controller.upsert_review")
class TestHandlePullRequestReviewComment(BaseClass):

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
        lock,
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
        lock,
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
        self.payload["action"] = "deleted"

        webhook._handle_pull_request_review_comment(self.payload)

        get_pull_request.assert_called_once_with(self.PULL_REQUEST_NODE_ID)
        upsert_review.assert_not_called()
        get_review_for_database_id.assert_called_once_with(
            self.PULL_REQUEST_NODE_ID, self.PULL_REQUEST_REVIEW_ID
        )
        delete_comment.assert_called_once_with(self.COMMENT_NODE_ID)

class GithubWebhookTest(MockDynamoDbTestCase):
    @patch.object(graphql_client, "get_pull_request_for_commit")
    @patch.object(github_controller, "upsert_pull_request")
    @patch.object(github_client, "merge_pull_request")
    def test_handle_status_webhook_ready_for_automerge(
        self,
        merge_pull_request_mock,
        upsert_pull_request_mock,
        get_pull_request_for_commit_mock,
    ):
        # Creating a pull request that can be automerged
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_SUCCESSFUL))
            .review(
                builder.review().submitted_at("2020-01-13T14:59:58Z").state("APPROVED")
            )
            .mergeable(True)
            .title("blah blah [shipit]")
        )

        existing_task_id = uuid4().hex
        dynamodb_client.insert_github_node_to_asana_id_mapping(
            pull_request.id(), existing_task_id
        )

        get_pull_request_for_commit_mock.return_value = pull_request

        webhook.handle_github_webhook(
            "status", pull_request.commits()[0].to_raw()
        )

        upsert_pull_request_mock.assert_not_called()
        merge_pull_request_mock.assert_called_with(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            pull_request.number(),
            pull_request.title(),
            pull_request.body(),
        )

    @patch.object(graphql_client, "get_pull_request_for_commit")
    @patch.object(github_controller, "upsert_pull_request")
    @patch.object(github_client, "merge_pull_request")
    def test_handle_status_webhook_not_ready_for_automerge(
        self,
        merge_pull_request_mock,
        upsert_pull_request_mock,
        get_pull_request_for_commit_mock,
    ):
        # Creating a pull request that can be automerged
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_FAILED))
            .review(
                builder.review().submitted_at("2020-01-13T14:59:58Z").state("APPROVED")
            )
            .mergeable(True)
            .title("blah blah [shipit]")
        )

        existing_task_id = uuid4().hex
        dynamodb_client.insert_github_node_to_asana_id_mapping(
            pull_request.id(), existing_task_id
        )

        get_pull_request_for_commit_mock.return_value = pull_request

        webhook.handle_github_webhook(
            "status", pull_request.commits()[0].to_raw()
        )

        upsert_pull_request_mock.assert_called_with(pull_request)
        merge_pull_request_mock.assert_not_called()


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
