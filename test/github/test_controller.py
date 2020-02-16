from unittest.mock import patch
from uuid import uuid4
from test.impl.mock_dynamodb_test_case import MockDynamoDbTestCase
import src.github.client as github_client
import src.github.controller as github_controller
import src.asana.controller as asana_controller
import src.dynamodb.client as dynamodb_client
from test.impl.builders import builder


class GithubControllerTest(MockDynamoDbTestCase):
    @patch.object(asana_controller, "update_task")
    @patch.object(asana_controller, "create_task")
    def test_upsert_pull_request_when_task_id_not_found_in_dynamodb(
        self, create_task_mock, update_task_mock
    ):
        # If the task id is not found in dynamodb, then we assume the task
        # doesn't exist and create a new task
        new_task_id = uuid4().hex
        create_task_mock.return_value = new_task_id

        pull_request = builder.pull_request().build()
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
        pull_request = builder.pull_request().build()

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
        pull_request = builder.pull_request("original body").build()
        task_id = uuid4().hex

        github_controller._add_asana_task_to_pull_request(pull_request, task_id)

        # Description was edited with the asana task in the body
        edit_pr_mock.assert_called()
        self.assertRegex(
            pull_request.body(),
            "original body\s*Pull Request synchronized with \[Asana task\]",
        )

    @patch.object(asana_controller, "update_task")
    @patch.object(asana_controller, "add_comment_to_task")
    def test_upsert_comment_when_task_id_already_found_in_dynamodb(
        self, add_comment_mock, update_task_mock
    ):
        # If the task id is found in dynamodb, then we just update (don't
        # attempt to create)
        pull_request = builder.pull_request().build()
        comment = builder.comment().build()

        # Insert the mapping first
        existing_task_id = uuid4().hex
        dynamodb_client.insert_github_node_to_asana_id_mapping(
            pull_request.id(), existing_task_id
        )

        github_controller.upsert_comment(pull_request, comment)

        add_comment_mock.assert_called_with(comment, existing_task_id)
        update_task_mock.assert_called_with(pull_request, existing_task_id)

    @patch.object(asana_controller, "update_task")
    @patch.object(asana_controller, "add_comment_to_task")
    def test_upsert_comment_when_task_id_not_found_in_dynamodb(
        self, add_comment_mock, update_task_mock
    ):
        pull_request = builder.pull_request().build()
        comment = builder.comment().build()

        github_controller.upsert_comment(pull_request, comment)
        # TODO: Test that a full sync was performed

    @patch.object(github_client, "set_pull_request_assignee")
    def test_assign_pull_request_to_author(self, set_pr_assignee_mock):
        user = builder.user().login("the_author").name("dont-care")
        pull_request = builder.pull_request().author(user).build()
        with patch.object(pull_request, "set_assignees") as set_assignees_mock:
            github_controller.assign_pull_request_to_author(pull_request)
            set_assignees_mock.assert_called_with([pull_request.author_handle()])

        set_pr_assignee_mock.assert_called_with(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            pull_request.number(),
            pull_request.author_handle(),
        )


if __name__ == '__main__':
    from unittest import main as run_tests
    run_tests()
