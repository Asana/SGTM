from unittest.mock import patch, ANY
from uuid import uuid4

import src.asana.controller as asana_controller
import src.aws.dynamodb_client as dynamodb_client
import src.aws.sqs_client as sqs_client
import src.github.client as github_client
import src.github.controller as github_controller
from src.github.models import ReviewState
from test.impl.builders import builder
from test.impl.mock_dynamodb_test_case import MockDynamoDbTestCase


@patch("src.aws.s3_client.get_asana_domain_user_id_from_github_handle")
class GithubControllerTest(MockDynamoDbTestCase):
    @patch.object(asana_controller, "update_task")
    @patch.object(asana_controller, "create_task")
    def test_upsert_pull_request_when_task_id_not_found_in_dynamodb(
        self,
        create_task_mock,
        update_task_mock,
        _get_asana_domain_id_mock,
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
        update_task_mock.assert_called_with(pull_request, new_task_id, ANY)

        # Assert that the new task id was inserted into the table
        task_id = dynamodb_client.get_asana_id_from_github_node_id(pull_request.id())
        self.assertEqual(task_id, new_task_id)

    @patch.object(asana_controller, "update_task")
    @patch.object(asana_controller, "create_task")
    def test_upsert_pull_request_when_task_id_already_found_in_dynamodb(
        self,
        create_task_mock,
        update_task_mock,
        _get_asana_domain_id_mock,
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
        update_task_mock.assert_called_with(pull_request, existing_task_id, ANY)

    @patch.object(github_client, "edit_pr_description")
    def test_add_asana_task_to_pull_request(
        self,
        edit_pr_mock,
        _get_asana_domain_id_mock,
    ):
        pull_request = builder.pull_request("original body").build()
        task_id = uuid4().hex

        github_controller._add_asana_task_to_pull_request(pull_request, task_id)

        # Description was edited with the asana task in the body
        edit_pr_mock.assert_called()
        self.assertRegex(
            pull_request.body(),
            "original body\s*Pull Request synchronized with \[Asana task\]",
        )

    @patch.object(asana_controller, "upsert_github_comment_to_task")
    def test_upsert_comment_when_task_id_already_found_in_dynamodb(
        self,
        add_comment_mock,
        _get_asana_domain_id_mock,
    ):
        # If the task id is found in dynamodb, then we just update (don't
        # attempt to create)
        pull_request = builder.pull_request().build()
        user = builder.user().login("the_author").name("dont-care")
        comment = builder.comment().author(user).build()
        org_name = "the-org"

        # Insert the mapping first
        existing_task_id = uuid4().hex
        dynamodb_client.insert_github_node_to_asana_id_mapping(
            pull_request.id(), existing_task_id
        )

        github_controller.upsert_comment(pull_request, comment, org_name)
        add_comment_mock.assert_called_with(comment, existing_task_id)

    @patch.object(sqs_client, "queue_full_sync")
    @patch.object(asana_controller, "upsert_github_comment_to_task")
    def test_queues_full_sync_on_approval_comment(
        self,
        add_comment_mock,
        queue_mock,
        _get_asana_domain_id_mock,
    ):
        # If the task id is found in dynamodb, then we just update (don't
        # attempt to create)
        pull_request = builder.pull_request().build()
        user = builder.user().login("the_author").name("dont-care")
        comment = builder.comment("LGTM").author(user).build()
        org_name = "the-org"

        # Insert the mapping first
        existing_task_id = uuid4().hex
        dynamodb_client.insert_github_node_to_asana_id_mapping(
            pull_request.id(), existing_task_id
        )

        github_controller.upsert_comment(pull_request, comment, org_name)
        add_comment_mock.assert_called_with(comment, existing_task_id)
        queue_mock.assert_called_with(pull_request.id(), org_name)

    @patch.object(sqs_client, "queue_full_sync")
    @patch.object(asana_controller, "upsert_github_comment_to_task")
    def test_upsert_comment_when_task_id_not_found_in_dynamodb(
        self,
        add_comment_mock,
        queue_mock,
        _get_asana_domain_id_mock,
    ):
        pull_request = builder.pull_request().build()
        user = builder.user().login("the_author").name("dont-care")
        comment = builder.comment().author(user).build()
        org_name = "the-org"

        github_controller.upsert_comment(pull_request, comment, org_name)
        add_comment_mock.assert_not_called()
        queue_mock.assert_called_with(pull_request.id(), org_name)

    @patch.object(asana_controller, "upsert_github_comment_to_task")
    def test_no_comment_when_made_by_bot(
        self,
        add_comment_mock,
        _get_asana_domain_id_mock,
    ):
        pull_request = builder.pull_request().build()
        bot_user = builder.user().login("the_author")
        comment = builder.comment("Blah").author(bot_user).build()

        # Insert the mapping first
        existing_task_id = uuid4().hex
        dynamodb_client.insert_github_node_to_asana_id_mapping(
            pull_request.id(), existing_task_id
        )

        github_controller.upsert_comment(pull_request, comment, org_name="organization")
        add_comment_mock.assert_not_called()

    @patch.object(asana_controller, "update_task")
    @patch.object(asana_controller, "upsert_github_review_to_task")
    @patch.object(github_client, "set_pull_request_assignee")
    def test_no_review_comment_when_made_by_bot(
        self,
        set_assignee_mock,
        add_review_mock,
        update_task_mock,
        _get_asana_domain_id_mock,
    ):
        author = builder.user().login("the_author").name("not-a-bot")
        pull_request = builder.pull_request().author(author).build()
        bot = builder.user().login("the_bot")
        review = builder.review("LGTM").author(bot).state(ReviewState.APPROVED).build()
        org_name = "the-org"

        # Insert the mapping first
        existing_task_id = uuid4().hex
        dynamodb_client.insert_github_node_to_asana_id_mapping(
            pull_request.id(), existing_task_id
        )

        github_controller.upsert_review(pull_request, review, org_name)
        add_review_mock.assert_not_called()
        set_assignee_mock.assert_called_with(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            pull_request.number(),
            pull_request.author_handle(),
        )

    @patch.object(github_client, "set_pull_request_assignee")
    def test_assign_pull_request_to_author(
        self, set_pr_assignee_mock, _get_asana_domain_id_mock
    ):
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


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
