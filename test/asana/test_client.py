import unittest
from unittest.mock import patch, Mock
import src.asana.client
from test.impl.base_test_case_class import BaseClass

asana_api_client = src.asana.client.AsanaClient.singleton().asana_api_client


class TestAsanaClientCreateTask(BaseClass):
    def test_create_task_requires_a_project_id(self):
        with self.assertRaises(ValueError):
            src.asana.client.create_task(None)
        with self.assertRaises(ValueError):
            src.asana.client.create_task("")
        with self.assertRaises(ValueError):
            src.asana.client.create_task(1)
        with self.assertRaises(ValueError):
            src.asana.client.create_task(1)

    def test_creates_task(self):
        task_id = "TASK_ID"
        with patch.object(
            asana_api_client.tasks, "create", return_value={"gid": task_id}
        ):
            actual = src.asana.client.create_task("PROJECT_ID")
            self.assertEqual(actual, task_id)

    def test_creates_task_in_correct_project(self):
        task_id = "TASK_ID"
        with patch.object(
            asana_api_client.tasks, "create", return_value={"gid": task_id}
        ) as create_task:
            src.asana.client.create_task("PROJECT_ID")
            create_task.assert_called_once_with({"projects": "PROJECT_ID"})

    def test_creates_task_with_due_date(self):
        task_id = "TASK_ID"
        with patch.object(
            asana_api_client.tasks, "create", return_value={"gid": task_id}
        ) as create_task:
            src.asana.client.create_task("PROJECT_ID", "Tomorrow")
            create_task.assert_called_once_with(
                {"projects": "PROJECT_ID", "due_on": "Tomorrow"}
            )


class TestAsanaClientUpdateTask(BaseClass):
    @unittest.skip  # temporarily swallow asana client exceptions
    def test_update_task_requires_a_task_id_and_fields(self):
        with self.assertRaises(ValueError):
            src.asana.client.update_task(None, {"a", "b"})
        with self.assertRaises(ValueError):
            src.asana.client.update_task("", {"a", "b"})
        with self.assertRaises(ValueError):
            src.asana.client.update_task(1, {"a", "b"})
        with self.assertRaises(ValueError):
            src.asana.client.update_task("a", None)
        with self.assertRaises(ValueError):
            src.asana.client.update_task("a", {})

    def test_updates_task(self):
        with patch.object(asana_api_client.tasks, "update") as update_task:
            src.asana.client.update_task("TASK_ID", {"FIELD": "VALUE"})
            update_task.assert_called_once_with("TASK_ID", {"FIELD": "VALUE"})


class TestAsanaClientCompleteTask(BaseClass):
    @unittest.skip  # temporarily swallow asana client exceptions
    def test_complete_task_requires_task_id(self):
        with self.assertRaises(ValueError):
            src.asana.client.complete_task(None)

    def test_completes_task(self):
        with patch.object(src.asana.client, "update_task") as update_task:
            src.asana.client.complete_task("TASK_ID")
            update_task.assert_called_once_with("TASK_ID", {"completed": True})


class TestAsanaClientAddFollowers(BaseClass):
    @unittest.skip  # temporarily swallow asana client exceptions
    def test_add_followers_requires_a_task_id_and_followers(self):
        with self.assertRaises(ValueError):
            src.asana.client.add_followers(None, ["a"])
        with self.assertRaises(ValueError):
            src.asana.client.add_followers("", ["a"])
        with self.assertRaises(ValueError):
            src.asana.client.add_followers(1, ["a"])
        with self.assertRaises(ValueError):
            src.asana.client.add_followers("1", None)
        with self.assertRaises(ValueError):
            src.asana.client.add_followers("1", [])
        with self.assertRaises(ValueError):
            src.asana.client.add_followers("1", [""])

    def test_adds_followers(self):
        with patch.object(asana_api_client.tasks, "add_followers") as add_followers:
            src.asana.client.add_followers("TASK_ID", ["FOLLOWER"])
            add_followers.assert_called_once_with(
                "TASK_ID", {"followers": ["FOLLOWER"]}
            )


class TestAsanaClientAddComment(BaseClass):
    @unittest.skip  # temporarily swallow asana client exceptions
    def test_add_comment_requires_a_task_id_and_comment_body(self):
        with self.assertRaises(ValueError):
            src.asana.client.add_comment(None, "body")
        with self.assertRaises(ValueError):
            src.asana.client.add_comment("", "body")
        with self.assertRaises(ValueError):
            src.asana.client.add_comment(1, "body")
        with self.assertRaises(ValueError):
            src.asana.client.add_comment("1", None)
        with self.assertRaises(ValueError):
            src.asana.client.add_comment("1", "")

    def test_adds_comment(self):
        with patch.object(asana_api_client.tasks, "add_comment") as add_comment:
            src.asana.client.add_comment("TASK_ID", "comment_body")
            add_comment.assert_called_once_with(
                "TASK_ID", {"html_text": "comment_body"}
            )


class TestAsanaClientUpdateComment(BaseClass):
    @unittest.skip  # temporarily swallow asana client exceptions
    def test_update_comment_requires_a_comment_id_and_comment_body(self):
        with self.assertRaises(ValueError):
            src.asana.client.update_comment(None, "body")
        with self.assertRaises(ValueError):
            src.asana.client.update_comment("comment_id", None)
        with self.assertRaises(ValueError):
            src.asana.client.update_comment("", "body")
        with self.assertRaises(ValueError):
            src.asana.client.update_comment("comment_id", "")

    @patch.object(asana_api_client.stories, "update")
    def test_updates_comment(self, update_story):
        src.asana.client.update_comment("COMMENT_ID", "comment_body")
        update_story.assert_called_once_with(
            "COMMENT_ID", {"html_text": "comment_body"}
        )


class TestAsanaClientDeleteComment(BaseClass):
    @unittest.skip  # temporarily swallow asana client exceptions
    def test_delete_comment_requires_a_comment_id(self):
        with self.assertRaises(ValueError):
            src.asana.client.delete_comment(None)
        with self.assertRaises(ValueError):
            src.asana.client.delete_comment("")

    @patch.object(asana_api_client.stories, "delete")
    def test_deletes_comment(self, delete_story):
        src.asana.client.delete_comment("COMMENT_ID")
        delete_story.assert_called_once_with("COMMENT_ID")


class TestAsanaClientFindAllTasksForProject(BaseClass):
    @patch.object(asana_api_client.tasks, "find_all")
    def test_find_all_tasks_for_project(self, find_all_mock):
        project_id = "12345"
        opt_fields = ["custom_fields"]
        src.asana.client.find_all_tasks_for_project(project_id, opt_fields)
        find_all_mock.assert_called_once_with(
            project=project_id, completed_since="now", opt_fields=opt_fields
        )


class TestAsanaClientCreateAttachmentOnTask(BaseClass):
    @patch.object(asana_api_client.attachments, "create_on_task")
    def test_create_on_task(self, create_attachment_on_task):
        src.asana.client.create_attachment_on_task(
            "1", "sample content", "sample_name.png"
        )
        create_attachment_on_task.assert_called_once_with(
            "1", "sample content", "sample_name.png", None
        )

    @patch.object(asana_api_client.attachments, "create_on_task")
    def test_create_on_task_with_image_type(self, create_attachment_on_task):
        src.asana.client.create_attachment_on_task(
            "1", "sample content", "sample_name.png", "image/png"
        )
        create_attachment_on_task.assert_called_once_with(
            "1", "sample content", "sample_name.png", "image/png"
        )


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
