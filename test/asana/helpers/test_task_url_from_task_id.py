import src.asana.helpers

from test.asana.helpers.base_class import BaseClass


class TestTaskUrlFromTaskId(BaseClass):

    def test_correct_by_default(self):
        task_id = "foo"
        task_url = src.asana.helpers.task_url_from_task_id(task_id)
        self.assertEqual(
            task_url,
            "https://app.asana.com/0/0/foo",
            "Expected task_url_from_task_id to refer to an Asana task")

    def test_none_causes_valueerror(self):
        try:
            src.asana.helpers.task_url_from_task_id(None)
            self.fail("This code should have been unreachable")
        except ValueError:
            pass

    def test_empty_string_causes_valueerror(self):
        try:
            src.asana.helpers.task_url_from_task_id("")
            self.fail("This code should have been unreachable")
        except ValueError:
            pass


if __name__ == '__main__':
    from unittest import main as run_tests
    run_tests()
