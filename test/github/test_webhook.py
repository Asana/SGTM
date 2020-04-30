from unittest.mock import patch
from uuid import uuid4
from test.impl.mock_dynamodb_test_case import MockDynamoDbTestCase
from test.impl.builders import builder, build
from src.github.models import Commit
import src.github.webhook as github_webhook
import src.github.graphql.client as graphql_client
import src.github.controller as github_controller
import src.github.client as github_client
import src.dynamodb.client as dynamodb_client


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

        github_webhook.handle_github_webhook(
            "status", pull_request.commits()[0].to_raw()
        )

        upsert_pull_request_mock.assert_called_with(pull_request)
        merge_pull_request_mock.assert_not_called()


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
