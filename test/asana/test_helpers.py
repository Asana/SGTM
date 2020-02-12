import unittest
from unittest.mock import patch

import src.asana.helpers
from test.github.helpers import PullRequestBuilder


class Memoize(unittest.TestCase):

    def test_decorated_functions_should_always_return_the_same_value(self):
        tmp_remember_me = 0

        @src.asana.helpers.memoize
        def remember_me():
            nonlocal tmp_remember_me
            tmp_remember_me += 1
            return tmp_remember_me
        self.assertEqual(1, remember_me(), "Expected remember_me to initially return 1")
        self.assertEqual(1, remember_me(), "Expected remember_me to always return 1 due to memoization")


class TaskUrlFromTaskId(unittest.TestCase):

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


class ExtractTaskFieldsFromPullRequest(unittest.TestCase):

    @patch("src.asana.helpers._asana_user_id_from_github_handle")
    def test_extracts_fields(self, _asana_user_id_from_github_handle):
        _asana_user_id_from_github_handle.return_value = "ASDF"
        builder = PullRequestBuilder()
        builder.raw_pr["number"] = "PR_NUMBER"
        builder.raw_pr["title"] = "PR_TITLE"
        pull_request = builder.build()
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual("#PR_TITLE - PR_NUMBER", task_fields["name"])

    def test_none_causes_valueerror(self):
        try:
            src.asana.helpers.extract_task_fields_from_pull_request(None)
            self.fail("This code should have been unreachable")
        except ValueError:
            pass


"""
def extract_task_fields_from_pull_request(pull_request: PullRequest) -> dict:
    if pull_request is None:
        raise ValueError("extract_task_fields_from_pull_request requires a pull_request")
    return {
        "assignee": _task_assignee_from_pull_request(pull_request),
        "name": _task_name_from_pull_request(pull_request),
        "html_notes": _task_description_from_pull_request(pull_request),
        "completed": _task_completion_from_pull_request(pull_request),
        "followers": _task_followers_from_pull_request(pull_request),
    }
"""

if __name__ == '__main__':
    unittest.main()
