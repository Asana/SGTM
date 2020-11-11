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


@patch("os.getenv")
@patch.object(github_client, "edit_pr_title")
@patch.object(github_client, "add_pr_comment")
class TestMaybeAddAutomergeWarningTitleAndComment(unittest.TestCase):
    SAMPLE_PR_TITLE = "Sample PR Title"

    def test_noop_if_feature_not_enabled(
        self, add_pr_comment_mock, edit_pr_title_mock, get_env_mock
    ):
        get_env_mock.return_value = "false"
        pull_request = build(
            builder.pull_request().label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
        )

        github_logic.maybe_add_automerge_warning_title_and_comment(pull_request)

        add_pr_comment_mock.assert_not_called()
        edit_pr_title_mock.assert_not_called()

    def test_does_not_add_warning_if_no_label(
        self, add_pr_comment_mock, edit_pr_title_mock, get_env_mock
    ):
        get_env_mock.return_value = "true"
        pull_request = build(builder.pull_request())

        github_logic.maybe_add_automerge_warning_title_and_comment(pull_request)

        add_pr_comment_mock.assert_not_called()
        edit_pr_title_mock.assert_not_called()

    def test_adds_warnings_if_label_and_no_warning_in_title(
        self, add_pr_comment_mock, edit_pr_title_mock, get_env_mock
    ):
        get_env_mock.return_value = "true"
        pull_request = build(
            builder.pull_request()
            .title(self.SAMPLE_PR_TITLE)
            .label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
        )

        github_logic.maybe_add_automerge_warning_title_and_comment(pull_request)

        edit_pr_title_mock.assert_called_with(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            pull_request.number(),
            self.SAMPLE_PR_TITLE + github_logic.AUTOMERGE_TITLE_WARNING,
        )
        add_pr_comment_mock.assert_called_with(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            pull_request.number(),
            github_logic.AUTOMERGE_COMMENT_WARNING,
        )

    def test_does_not_add_warning_if_has_label_and_already_has_warning_in_title(
        self, add_pr_comment_mock, edit_pr_title_mock, get_env_mock
    ):
        get_env_mock.return_value = "true"
        pull_request = build(
            builder.pull_request()
            .title(self.SAMPLE_PR_TITLE + github_logic.AUTOMERGE_TITLE_WARNING)
            .label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
        )

        github_logic.maybe_add_automerge_warning_title_and_comment(pull_request)

        edit_pr_title_mock.assert_not_called()
        add_pr_comment_mock.assert_not_called()

    def test_does_not_add_warning_comment_if_label_does_not_require_approval(
        self, add_pr_comment_mock, edit_pr_title_mock, get_env_mock
    ):
        get_env_mock.return_value = "true"
        pull_request = build(
            builder.pull_request()
            .title(self.SAMPLE_PR_TITLE)
            .label(builder.label().name(github_logic.AutomergeLabel.AFTER_TESTS.value))
        )

        github_logic.maybe_add_automerge_warning_title_and_comment(pull_request)

        edit_pr_title_mock.assert_called_with(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            pull_request.number(),
            self.SAMPLE_PR_TITLE + github_logic.AUTOMERGE_TITLE_WARNING,
        )
        add_pr_comment_mock.assert_not_called()

    def test_removes_title_warning_if_label_removed(
        self, add_pr_comment_mock, edit_pr_title_mock, get_env_mock
    ):
        get_env_mock.return_value = "true"
        pull_request = build(
            builder.pull_request().title(
                self.SAMPLE_PR_TITLE + github_logic.AUTOMERGE_TITLE_WARNING
            )
        )

        github_logic.maybe_add_automerge_warning_title_and_comment(pull_request)

        edit_pr_title_mock.assert_called_with(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            pull_request.number(),
            self.SAMPLE_PR_TITLE,
        )
        add_pr_comment_mock.assert_not_called()


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
