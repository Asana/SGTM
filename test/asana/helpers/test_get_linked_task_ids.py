from src.asana import helpers as asana_helpers

from test.impl.builders import builder, build
from test.impl.base_test_case_class import BaseClass
from functools import reduce


class TestGetLinkedTaskIds(BaseClass):
    def test_gets_many_task_ids(self):
        task_ids = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        url_list = [
            f"https://app.asana.com/0/1162076285812014/{id}/f " for id in task_ids
        ]
        url_string = reduce(lambda url_str, url: url_str + url, url_list)
        pull_request = build(
            builder.pull_request().body(
                f"Blah blah blah\nblah\n\
                Asana tasks:\n{url_string}"
            )
        )

        self.assertCountEqual(asana_helpers.get_linked_task_ids(pull_request), task_ids)

    def test_returns_empty_list_if_no_asana_tasks_line(self):
        pull_request = build(builder.pull_request().body(f"Blah blah blah\nblah\n"))

        self.assertCountEqual(asana_helpers.get_linked_task_ids(pull_request), [])

    def test_returns_empty_list_if_no_linked_tasks(self):
        pull_request = build(
            builder.pull_request().body(f"Blah blah blah\nblah\nAsana tasks:")
        )

        self.assertCountEqual(asana_helpers.get_linked_task_ids(pull_request), [])

    def test_returns_empty_list_for_malformed_description(self):
        pull_request = build(
            builder.pull_request().body(f"Blah blah blah\nblah\nAsana tasks:\neng jank")
        )

        self.assertCountEqual(asana_helpers.get_linked_task_ids(pull_request), [])


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
