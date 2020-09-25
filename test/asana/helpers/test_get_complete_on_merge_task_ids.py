from src.asana import helpers as asana_helpers

from test.impl.builders import builder, build
from test.impl.base_test_case_class import BaseClass


class TestGetCompleteOnMergeTaskIds(BaseClass):
    def test_gets_multiple_task_ids(self):
        task_ids = ["1193030527856669", "1193030527856669"]
        pull_request = build(
            builder.pull_request().body(
                f"Blah blah blah\nblah\n\
                Tasks to complete on merge: [#{task_ids[0]}](https://app.asana.com/0/1162076285812014/{task_ids[0]}/f), \
                [#{task_ids[1]}](https://app.asana.com/0/1162076285812014/{task_ids[1]}/f)"
            )
        )

        self.assertCountEqual(
            asana_helpers.get_complete_on_merge_task_ids(pull_request), task_ids
        )

    def test_returns_empty_list_if_no_tasks_to_complete_line(self):
        pull_request = build(builder.pull_request().body(f"Blah blah blah\nblah\n"))

        self.assertCountEqual(
            asana_helpers.get_complete_on_merge_task_ids(pull_request), []
        )

    def test_returns_empty_list_if_no_tasks_to_complete(self):
        pull_request = build(
            builder.pull_request().body(
                f"Blah blah blah\nblah\nTasks to complete on merge:"
            )
        )

        self.assertCountEqual(
            asana_helpers.get_complete_on_merge_task_ids(pull_request), []
        )


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()