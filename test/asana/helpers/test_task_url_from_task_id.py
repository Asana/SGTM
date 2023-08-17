import unittest
import src.asana.helpers
from test.impl.base_test_case_class import BaseClass


class TestTaskUrlFromTaskId(BaseClass):
    @unittest.skip  # type: ignore
    def test_task_url_from_task_id_requires_a_task_id(self):
        with self.assertRaises(ValueError):
            src.asana.helpers.task_url_from_task_id("")

    def test_correct_by_default(self):
        task_id = "foo"
        task_url = src.asana.helpers.task_url_from_task_id(task_id)
        self.assertEqual(
            task_url,
            "https://app.asana.com/0/0/foo",
            "Expected task_url_from_task_id to refer to an Asana task",
        )


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
