from unittest.mock import patch
from uuid import uuid4
from datetime import datetime, timedelta
from test.mock_test_case import MockTestCase
import src.github.client as github_client
import src.github.logic as github_logic
import src.github.controller as github_controller
import src.asana.controller as asana_controller
import src.dynamodb.client as dynamodb_client
from src.github.models import Review
from test.github.helpers import (
    PullRequestBuilder,
    ReviewBuilder,
    CommentBuilder,
)


class GithubControllerTest(MockTestCase):
    @patch.object(asana_controller, "update_task")
    @patch.object(asana_controller, "create_task")
    def test_upsert_pull_request_when_task_id_not_found_in_dynamodb(
        self, create_task_mock, update_task_mock
    ):
        # If the task id is not found in dynamodb, then we assume the task
        # doesn't exist and create a new task
        new_task_id = uuid4().hex
        create_task_mock.return_value = new_task_id

        pull_request = PullRequestBuilder().build()
        with patch.object(
            github_controller, "_add_asana_task_to_pull_request"
        ) as add_asana_task_to_pr_mock:
            github_controller.upsert_pull_request(pull_request)
            add_asana_task_to_pr_mock.assert_called_with(pull_request, new_task_id)

        create_task_mock.assert_called_with(pull_request.repository_id())
        update_task_mock.assert_called_with(pull_request, new_task_id)

        # Assert that the new task id was inserted into the table
        task_id = dynamodb_client.get_asana_id_from_github_node_id(pull_request.id())
        self.assertEqual(task_id, new_task_id)

    @patch.object(asana_controller, "update_task")
    @patch.object(asana_controller, "create_task")
    def test_upsert_pull_request_when_task_id_already_found_in_dynamodb(
        self, create_task_mock, update_task_mock
    ):
        # If the task id is found in dynamodb, then we just update (don't
        # attempt to create)
        pull_request = PullRequestBuilder().build()

        # Insert the mapping first
        existing_task_id = uuid4().hex
        dynamodb_client.insert_github_node_to_asana_id_mapping(
            pull_request.id(), existing_task_id
        )

        github_controller.upsert_pull_request(pull_request)

        create_task_mock.assert_not_called()
        update_task_mock.assert_called_with(pull_request, existing_task_id)

    @patch.object(github_client, "edit_pr_description")
    def test_add_asana_task_to_pull_request(self, edit_pr_mock):
        pull_request = PullRequestBuilder("original body").build()
        task_id = uuid4().hex

        github_controller._add_asana_task_to_pull_request(pull_request, task_id)

        # Description was edited with the asana task in the body
        edit_pr_mock.assert_called()
        self.assertRegex(
            pull_request.body(),
            "original body\s*Pull Request synchronized with \[Asana task\]",
        )

    # TODO: More tests for this module
