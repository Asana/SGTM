from unittest.mock import patch, Mock, MagicMock, call
from test.impl.builders import builder, build
from datetime import datetime


from test.impl.base_test_case_class import BaseClass

from src.github.models import Review, Comment
from src.asana import controller


@patch("src.asana.helpers.asana_comment_from_github_review")
@patch("src.asana.client.add_comment")
@patch("src.dynamodb.client.insert_github_node_to_asana_id_mapping")
@patch("src.dynamodb.client.bulk_insert_github_node_to_asana_id_mapping")
class TestUpsertGithubReviewToTask(BaseClass):
    REVIEW_ID = "12345"
    ASANA_COMMENT_ID = "56789"
    ASANA_TASK_ID = "abcde"
    ASANA_COMMENT_BODY = "<body>Here's a comment</body>"

    def _mock_comment(self, id):
        return MagicMock(spec=Comment, id=MagicMock(return_value=id))

    def _mock_review(self, id, comments=[]):
        return MagicMock(
            spec=Review,
            id=MagicMock(return_value=id),
            comments=MagicMock(return_value=comments),
        )

    @patch("src.dynamodb.client.get_asana_id_from_github_node_id", return_value=None)
    def test_created_review_with_no_comments(
        self,
        get_asana_id_from_github_node_id,
        bulk_insert_github_node_to_asana_id_mapping,
        insert_github_node_to_asana_id_mapping,
        add_comment,
        asana_comment_from_github_review,
    ):
        review = self._mock_review(self.REVIEW_ID)
        asana_comment_from_github_review.return_value = self.ASANA_COMMENT_BODY

        add_comment.return_value = self.ASANA_COMMENT_ID

        controller.upsert_github_review_to_task(review, self.ASANA_TASK_ID)

        add_comment.assert_called_once_with(self.ASANA_TASK_ID, self.ASANA_COMMENT_BODY)
        asana_comment_from_github_review.assert_called_once_with(review)
        insert_github_node_to_asana_id_mapping.assert_called_once_with(
            self.REVIEW_ID, self.ASANA_COMMENT_ID
        )
        get_asana_id_from_github_node_id.assert_called_once_with(self.REVIEW_ID)

    @patch("src.dynamodb.client.get_asana_id_from_github_node_id", return_value=None)
    def test_created_review_with_comments(
        self,
        get_asana_id_from_github_node_id,
        bulk_insert_github_node_to_asana_id_mapping,
        insert_github_node_to_asana_id_mapping,
        add_comment,
        asana_comment_from_github_review,
    ):
        review = self._mock_review(
            self.REVIEW_ID, [self._mock_comment("123"), self._mock_comment("456")]
        )
        asana_comment_from_github_review.return_value = self.ASANA_COMMENT_BODY

        add_comment.return_value = self.ASANA_COMMENT_ID

        controller.upsert_github_review_to_task(review, self.ASANA_TASK_ID)

        insert_github_node_to_asana_id_mapping.assert_called_once_with(
            self.REVIEW_ID, self.ASANA_COMMENT_ID
        )
        bulk_insert_github_node_to_asana_id_mapping.assert_called_once_with(
            [("123", self.ASANA_COMMENT_ID), ("456", self.ASANA_COMMENT_ID)]
        )
        add_comment.assert_called_once_with(self.ASANA_TASK_ID, self.ASANA_COMMENT_BODY)
        get_asana_id_from_github_node_id.assert_called_once_with(self.REVIEW_ID)
        asana_comment_from_github_review.assert_called_once_with(review)

    @patch("src.asana.client.update_comment")
    @patch(
        "src.dynamodb.client.get_asana_id_from_github_node_id",
        return_value=ASANA_COMMENT_ID,
    )
    def test_updated_review_with_comments(
        self,
        get_asana_id_from_github_node_id,
        update_comment,
        bulk_insert_github_node_to_asana_id_mapping,
        insert_github_node_to_asana_id_mapping,
        add_comment,
        asana_comment_from_github_review,
    ):
        review = self._mock_review(
            self.REVIEW_ID, [self._mock_comment("123"), self._mock_comment("456")]
        )
        asana_comment_from_github_review.return_value = self.ASANA_COMMENT_BODY

        controller.upsert_github_review_to_task(review, self.ASANA_TASK_ID)

        get_asana_id_from_github_node_id.assert_called_once_with(self.REVIEW_ID)
        asana_comment_from_github_review.assert_called_once_with(review)
        update_comment.assert_called_once_with(
            self.ASANA_COMMENT_ID, self.ASANA_COMMENT_BODY
        )
        bulk_insert_github_node_to_asana_id_mapping.assert_called_once_with(
            [("123", self.ASANA_COMMENT_ID), ("456", self.ASANA_COMMENT_ID)]
        )
        add_comment.assert_not_called()


class TestNewDueOnOrNone(BaseClass):
    def test_new_assignee_due_on_change(self):
        task = {"assignee": {"gid": "123"}, "due_on": "2010-01-01"}
        update_task_fields = {"assignee": "321"}
        self.assertEqual(
            controller._new_due_on_or_none(task, update_task_fields),
            datetime.now().strftime("%Y-%m-%d"),
        )

    def test_new_assignee_due_on_in_the_future(self):
        future_due_on = "3000-01-01"
        task = {"assignee": {"gid": "123"}, "due_on": future_due_on}
        update_task_fields = {"assignee": "321"}
        self.assertEqual(controller._new_due_on_or_none(task, update_task_fields), None)

    def test_same_assignee(self):
        assignee_gid = "123"
        task = {"assignee": {"gid": assignee_gid}, "due_on": "2010-01-01"}
        update_task_fields = {"assignee": assignee_gid}
        self.assertEqual(controller._new_due_on_or_none(task, update_task_fields), None)


@patch("src.asana.client.complete_task")
@patch("src.asana.helpers.get_linked_task_ids")
@patch("src.asana.logic.should_autocomplete_tasks_on_merge", return_value=True)
class TestMaybeCompleteTasksOnMerge(BaseClass):
    def test_noop_if_no_task_ids_to_complete(
        self,
        should_autocomplete_tasks_on_merge_mock,
        get_linked_task_ids_mock,
        complete_task_mock,
    ):
        get_linked_task_ids_mock.return_value = []
        pull_request = build(builder.pull_request().merged(True))
        controller.maybe_complete_tasks_on_merge(pull_request)
        complete_task_mock.assert_not_called()

    def test_updates_tasks_with_completed_true_if_has_task_id(
        self,
        should_autocomplete_tasks_on_merge_mock,
        get_linked_task_ids_mock,
        complete_task_mock,
    ):
        task_ids = ["123", "456"]
        get_linked_task_ids_mock.return_value = task_ids
        pull_request = build(builder.pull_request().merged(True))
        controller.maybe_complete_tasks_on_merge(pull_request)
        complete_task_mock.assert_any_call(task_ids[0])
        complete_task_mock.assert_any_call(task_ids[1])


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
