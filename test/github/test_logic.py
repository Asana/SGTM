import unittest
from unittest.mock import patch
import src.github.logic as github_logic
from src.github.models import Commit, ReviewState, PullRequest, MergeableState
from test.impl.builders import builder, build
import src.github.controller as github_controller
import src.github.client as github_client


@patch.object(github_controller, "upsert_pull_request")
@patch.object(github_client, "merge_pull_request")
@patch.object(github_logic, "_is_pull_request_ready_for_automerge")
class TestMaybeAutomergePullRequest(unittest.TestCase):
    def test_handle_status_webhook_ready_for_automerge(
        self,
        is_pull_request_ready_for_automerge_mock,
        merge_pull_request_mock,
        upsert_pull_request_mock,
    ):
        # Mock that pull request can be automerged
        is_pull_request_ready_for_automerge_mock.return_value = True
        pull_request = build(builder.pull_request())

        merged = github_logic.maybe_automerge_pull_request(pull_request)

        self.assertTrue(merged)
        merge_pull_request_mock.assert_called_with(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            pull_request.number(),
            pull_request.title(),
            pull_request.body(),
        )

    def test_handle_status_webhook_not_ready_for_automerge(
        self,
        is_pull_request_ready_for_automerge_mock,
        merge_pull_request_mock,
        upsert_pull_request_mock,
    ):
        # Mock that pull request cannot be automerged
        is_pull_request_ready_for_automerge_mock.return_value = False
        pull_request = build(builder.pull_request())

        merged = github_logic.maybe_automerge_pull_request(pull_request)

        self.assertFalse(merged)
        merge_pull_request_mock.assert_not_called()


class TestPullRequestHasLabel(unittest.TestCase):
    def test_pull_request_with_label(self):
        label_name = "test label"
        pull_request = build(
            builder.pull_request().label(builder.label().name(label_name))
        )

        self.assertTrue(github_logic._pull_request_has_label(pull_request, label_name))

    def test_pull_request_without_label(self):
        label_name = "test label"
        pull_request = build(builder.pull_request())

        self.assertFalse(github_logic._pull_request_has_label(pull_request, label_name))


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
