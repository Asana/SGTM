from src.asana import helpers as asana_helpers
from test.impl.builders import builder, build

from test.impl.base_test_case_class import BaseClass


class TestTaskStatusFromPullRequest(BaseClass):
    def test_closed(self):
        pull_request = build(builder.pull_request().closed(True).merged(False))
        task_status = asana_helpers._task_status_from_pull_request(pull_request)
        self.assertEqual("Closed", task_status)

    def test_merged(self):
        pull_request = build(builder.pull_request().closed(True).merged(True))
        task_status = asana_helpers._task_status_from_pull_request(pull_request)
        self.assertEqual("Merged", task_status)

    def test_open(self):
        pull_request = build(builder.pull_request().closed(False).merged(False))
        task_status = asana_helpers._task_status_from_pull_request(pull_request)
        self.assertEqual("Open", task_status)

    def test_draft(self):
        pull_request = build(
            builder.pull_request().closed(False).merged(False).isDraft(True)
        )
        task_status = asana_helpers._task_status_from_pull_request(pull_request)
        self.assertEqual("Draft", task_status)


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
