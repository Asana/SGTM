import unittest
from unittest.mock import patch
import src.github.logic as github_logic
from src.github.models import Commit, ReviewState, PullRequest, MergeableState
from test.impl.builders import builder, build
import src.github.controller as github_controller
import src.github.client as github_client
from src.github.helpers import pull_request_has_label


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

@patch.object(github_client, "add_pr_comment")
@patch.object(github_controller, "upsert_pull_request")
@patch.object(github_client, "merge_pull_request")
class TestIsPullRequestReadyForAutomerge(unittest.TestCase):
    def test_handle_status_webhook_not_ready_for_automerge_due_to_conflict(
        self,
        merge_pull_request_mock,
        upsert_pull_request_mock,
        add_pr_comment_mock
    ):
        pull_request = build(
            builder.pull_request()
            .title("Sample PR")
            .merged(False)
            .mergeable(MergeableState.CONFLICTING)
            .commit(builder.commit().status(Commit.BUILD_SUCCESSFUL))
            .reviews([
                builder.review()
                .submitted_at("2020-01-13T14:59:57Z")
                .state(ReviewState.APPROVED)
            ])
            .label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
        )

        merged = github_logic._is_pull_request_ready_for_automerge(pull_request)

        self.assertFalse(merged)
        merge_pull_request_mock.assert_not_called()

        add_pr_comment_mock.assert_called_with(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            pull_request.number(),
            github_logic.AUTOMERGE_CONFLICT_COMMENT_WARNING,
        )


class TestPullRequestHasLabel(unittest.TestCase):
    def test_pull_request_with_label(self):
        label_name = "test label"
        pull_request = build(
            builder.pull_request().label(builder.label().name(label_name))
        )

        self.assertTrue(github_logic.pull_request_has_label(pull_request, label_name))

    def test_pull_request_without_label(self):
        label_name = "test label"
        pull_request = build(builder.pull_request())

        self.assertFalse(github_logic.pull_request_has_label(pull_request, label_name))


@patch.object(github_client, "edit_pr_title")
@patch.object(github_client, "add_pr_comment")
class TestMaybeAddAutomergeWarningAndComment(unittest.TestCase):
    SAMPLE_PR_TITLE = "Sample PR Title"

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", False)
    def test_noop_if_feature_not_enabled(self, add_pr_comment_mock, edit_pr_title_mock):
        pull_request = build(
            builder.pull_request().label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
        )

        github_logic.maybe_add_automerge_warning_comment(pull_request)

        add_pr_comment_mock.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_does_not_add_warning_if_no_label(
        self, add_pr_comment_mock, edit_pr_title_mock
    ):
        pull_request = build(builder.pull_request())

        github_logic.maybe_add_automerge_warning_comment(pull_request)

        add_pr_comment_mock.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_adds_warnings_if_label_and_no_warning_in_comments(
        self, add_pr_comment_mock, edit_pr_title_mock
    ):
        pull_request = build(
            builder.pull_request()
            .title(self.SAMPLE_PR_TITLE)
            .label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
        )

        github_logic.maybe_add_automerge_warning_comment(pull_request)

        add_pr_comment_mock.assert_called_with(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            pull_request.number(),
            github_logic.AUTOMERGE_COMMENT_WARNING,
        )

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_does_not_add_warning_if_has_label_and_already_has_warning_in_comments(
        self, add_pr_comment_mock, edit_pr_title_mock
    ):
        pull_request = build(
            builder.pull_request()
            .comments(
                [
                    builder.comment()
                    .author(builder.user("github_unknown_user_login"))
                    .body(github_logic.AUTOMERGE_COMMENT_WARNING)
                ]
            )
            .label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
        )

        github_logic.maybe_add_automerge_warning_comment(pull_request)

        edit_pr_title_mock.assert_not_called()
        add_pr_comment_mock.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_does_not_add_warning_comment_if_label_does_not_require_approval(
        self, add_pr_comment_mock, edit_pr_title_mock
    ):
        pull_request = build(
            builder.pull_request()
            .title(self.SAMPLE_PR_TITLE)
            .label(builder.label().name(github_logic.AutomergeLabel.AFTER_TESTS.value))
        )

        github_logic.maybe_add_automerge_warning_comment(pull_request)

        add_pr_comment_mock.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_does_not_add_warning_comment_if_pr_is_approved(
        self, add_pr_comment_mock, edit_pr_title_mock
    ):
        pull_request = build(
            builder.pull_request()
            .title(self.SAMPLE_PR_TITLE)
            .label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.APPROVED)
            )
        )

        github_logic.maybe_add_automerge_warning_comment(pull_request)

        add_pr_comment_mock.assert_not_called()


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
