import unittest
from unittest.mock import patch
import src.github.logic as github_logic
from src.github.models import Commit, ReviewState, MergeableState
from test.impl.builders import builder, build
import src.github.client as github_client


@patch.object(github_client, "merge_pull_request")
@patch("src.github.logic.SGTM_FEATURE__CHECK_RERUN_THRESHOLD_HOURS", 0)
class TestMaybeAutomergePullRequest(unittest.TestCase):
    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_after_tests_and_approval(
        self,
        mock_merge_pull_request,
    ):
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_SUCCESSFUL))
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.APPROVED)
            )
            .mergeable(MergeableState.MERGEABLE)
            .merged(False)
            .label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
        )
        self.assertTrue(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_called_once_with(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            pull_request.number(),
            pull_request.title(),
            pull_request.body(),
        )

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_after_approval(
        self, mock_merge_pull_request
    ):
        pull_request = build(
            builder.pull_request()
            .commit(
                builder.commit().status(Commit.BUILD_PENDING)
            )  # build hasn't finished, but PR is approved
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.APPROVED)
            )
            .mergeable(MergeableState.MERGEABLE)
            .merged(False)
            .label(
                builder.label().name(github_logic.AutomergeLabel.AFTER_APPROVAL.value)
            )
        )
        self.assertTrue(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_called_once()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_after_tests(
        self, mock_merge_pull_request
    ):
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_SUCCESSFUL))
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.CHANGES_REQUESTED)
            )
            .mergeable(MergeableState.MERGEABLE)
            .merged(False)
            .label(builder.label().name(github_logic.AutomergeLabel.AFTER_TESTS.value))
        )
        self.assertTrue(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_called_once()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_immediately(
        self, mock_merge_pull_request
    ):
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_FAILED))
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.CHANGES_REQUESTED)
            )
            .mergeable(MergeableState.UNKNOWN)
            .merged(False)
            .label(builder.label().name(github_logic.AutomergeLabel.IMMEDIATELY.value))
        )
        self.assertTrue(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_called_once()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_immediately_conflicting(
        self, mock_merge_pull_request
    ):
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_FAILED))
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.CHANGES_REQUESTED)
            )
            .mergeable(MergeableState.CONFLICTING)
            .merged(False)
            .label(builder.label().name(github_logic.AutomergeLabel.IMMEDIATELY.value))
        )
        self.assertFalse(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", False)
    def test_is_pull_request_ready_for_automerge_autofail_if_feature_not_enabled(
        self, mock_merge_pull_request
    ):
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_SUCCESSFUL))
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.APPROVED)
            )
            .mergeable(MergeableState.MERGEABLE)
            .merged(False)
            .label(builder.label().name(github_logic.AutomergeLabel.IMMEDIATELY.value))
        )
        self.assertFalse(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_autofail_if_merged(
        self, mock_merge_pull_request
    ):
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_SUCCESSFUL))
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.APPROVED)
            )
            .mergeable(MergeableState.MERGEABLE)
            .merged(True)
            .closed(False)
            .label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
        )
        self.assertFalse(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_autofail_if_closed(
        self, mock_merge_pull_request
    ):
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_SUCCESSFUL))
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.APPROVED)
            )
            .mergeable(MergeableState.MERGEABLE)
            .merged(False)
            .closed(True)
            .label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
        )
        self.assertFalse(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_build_failed(
        self, mock_merge_pull_request
    ):
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_FAILED))
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.APPROVED)
            )
            .mergeable(MergeableState.MERGEABLE)
            .merged(False)
            .label(builder.label().name(github_logic.AutomergeLabel.AFTER_TESTS.value))
        )
        self.assertFalse(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_build_pending(
        self, mock_merge_pull_request
    ):
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_PENDING))
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.APPROVED)
            )
            .mergeable(MergeableState.MERGEABLE)
            .merged(False)
            .label(builder.label().name(github_logic.AutomergeLabel.AFTER_TESTS.value))
        )
        self.assertFalse(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_after_approval_reviewer_requested_changes(
        self, mock_merge_pull_request
    ):
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_SUCCESSFUL))
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.CHANGES_REQUESTED)
            )
            .mergeable(MergeableState.MERGEABLE)
            .merged(False)
            .label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
        )
        self.assertFalse(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_after_requested_changes_then_approved(
        self, mock_merge_pull_request
    ):
        author_1 = builder.user().login("author_1")
        author_2 = builder.user().login("author_2")
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_SUCCESSFUL))
            .reviews(
                [
                    builder.review()
                    .submitted_at("2020-01-12T14:59:58Z")
                    .state(ReviewState.APPROVED)
                    .author(author_2),
                    builder.review()
                    .submitted_at("2020-01-13T14:59:58Z")
                    .state(ReviewState.CHANGES_REQUESTED)
                    .author(author_1),
                ]
            )
            .mergeable(MergeableState.MERGEABLE)
            .merged(False)
            .label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
        )
        self.assertFalse(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_after_approved_then_requested_changes(
        self, mock_merge_pull_request
    ):
        author_1 = builder.user().login("author_1")
        author_2 = builder.user().login("author_2")
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_SUCCESSFUL))
            .reviews(
                [
                    builder.review()
                    .submitted_at("2020-01-11T14:59:58Z")
                    .state(ReviewState.CHANGES_REQUESTED)
                    .author(author_1),
                    builder.review()
                    .submitted_at("2020-01-12T14:59:58Z")
                    .state(ReviewState.APPROVED)
                    .author(author_2),
                ]
            )
            .mergeable(MergeableState.MERGEABLE)
            .merged(False)
            .label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
        )
        self.assertTrue(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_changes_after_approval_requested_then_approval(
        self, mock_merge_pull_request
    ):
        author_1 = builder.user().login("author_1")
        author_2 = builder.user().login("author_2")
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_SUCCESSFUL))
            .reviews(
                [
                    builder.review()
                    .submitted_at("2020-01-11T14:59:58Z")
                    .state(ReviewState.CHANGES_REQUESTED)
                    .author(author_1),
                    builder.review()
                    .submitted_at("2020-01-12T14:59:58Z")
                    .state(ReviewState.APPROVED)
                    .author(author_2),
                    builder.review()
                    .submitted_at("2020-01-13T14:59:58Z")
                    .state(ReviewState.APPROVED)
                    .author(author_1),
                ]
            )
            .mergeable(MergeableState.MERGEABLE)
            .merged(False)
            .label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
        )
        self.assertTrue(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_called_once()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_after_tests_no_review(
        self, mock_merge_pull_request
    ):
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_SUCCESSFUL))
            .title("blah blah [shipit]")
            .mergeable(MergeableState.MERGEABLE)
            .merged(False)
            .label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
        )
        self.assertFalse(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_after_approval_no_review(
        self, mock_merge_pull_request
    ):
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_SUCCESSFUL))
            .title("blah blah [shipit]")
            .mergeable(MergeableState.MERGEABLE)
            .merged(False)
            .label(builder.label().name(github_logic.AutomergeLabel.AFTER_TESTS.value))
        )
        self.assertTrue(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_called_once()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_no_automerge_label(
        self, mock_merge_pull_request
    ):
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_SUCCESSFUL))
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.APPROVED)
            )
            .mergeable(MergeableState.MERGEABLE)
            .merged(False)
            .label(builder.label().name("random label"))
        )
        self.assertFalse(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_after_approval_mergeable_is_false(
        self, mock_merge_pull_request
    ):
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_SUCCESSFUL))
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.APPROVED)
            )
            .mergeable(MergeableState.CONFLICTING)
            .merged(False)
            .label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
        )
        self.assertFalse(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_after_tests_mergeable_is_false(
        self, mock_merge_pull_request
    ):
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_SUCCESSFUL))
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.APPROVED)
            )
            .mergeable(MergeableState.CONFLICTING)
            .merged(False)
            .label(builder.label().name(github_logic.AutomergeLabel.AFTER_TESTS.value))
        )
        self.assertFalse(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_not_called()


@patch.object(github_client, "rerequest_check_run")
class TestMaybeRerunStaleRequiredChecks(unittest.TestCase):
    @patch("src.github.logic.SGTM_FEATURE__CHECK_RERUN_THRESHOLD_HOURS", 0)
    def test_maybe_rerun_stale_checks_feature_disabled(self, mock_rerequest_check_run):
        pull_request = build(builder.pull_request())
        self.assertFalse(github_logic._maybe_rerun_stale_checks(pull_request))
        mock_rerequest_check_run.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__CHECK_RERUN_THRESHOLD_HOURS", 1)
    def test_maybe_rerun_stale_checks_no_base_ref(self, mock_rerequest_check_run):
        pull_request = build(builder.pull_request().base_ref_name("master"))
        self.assertFalse(github_logic._maybe_rerun_stale_checks(pull_request))
        mock_rerequest_check_run.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__CHECK_RERUN_THRESHOLD_HOURS", 1)
    @patch("src.github.logic.SGTM_FEATURE__CHECK_RERUN_BASE_REF_NAMES", ["master"])
    def test_maybe_rerun_stale_checks_for_old_pr(self, mock_rerequest_check_run):
        check_run = build(builder.check_run().completed_at("2020-01-13T14:59:58Z"))
        pull_request = build(
            builder.pull_request()
            .base_ref_name("master")
            .commit(
                builder.commit()
                .status(Commit.BUILD_SUCCESSFUL)
                .check_suites([builder.check_suite().check_runs([check_run])])
            )
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.APPROVED)
            )
            .mergeable(MergeableState.MERGEABLE)
            .merged(False)
            .label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
        )
        self.assertTrue(github_logic._maybe_rerun_stale_checks(pull_request))
        mock_rerequest_check_run.assert_called_once_with(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            check_run.database_id(),
        )

    @patch("src.github.logic.SGTM_FEATURE__CHECK_RERUN_THRESHOLD_HOURS", 1)
    @patch("src.github.logic.SGTM_FEATURE__CHECK_RERUN_BASE_REF_NAMES", ["master"])
    def test_maybe_rerun_stale_checks_once_per_check_suite(
        self, mock_rerequest_check_run
    ):
        check_run = build(builder.check_run().completed_at("2020-01-13T14:59:58Z"))
        pull_request = build(
            builder.pull_request()
            .base_ref_name("master")
            .commit(
                builder.commit()
                .status(Commit.BUILD_SUCCESSFUL)
                .check_suites(
                    [builder.check_suite().check_runs([check_run, check_run])]
                )
            )
        )
        self.assertTrue(github_logic._maybe_rerun_stale_checks(pull_request))
        mock_rerequest_check_run.assert_called_once_with(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            check_run.database_id(),
        )

    @patch("src.github.logic.SGTM_FEATURE__CHECK_RERUN_THRESHOLD_HOURS", 1)
    @patch(
        "src.github.logic.SGTM_FEATURE__CHECK_RERUN_BASE_REF_NAMES",
        ["master", "main", "test"],
    )
    def test_maybe_rerun_stale_checks_multiple_base_refs(
        self, mock_rerequest_check_run
    ):
        check_run = build(builder.check_run().completed_at("2020-01-13T14:59:58Z"))
        pull_request_main = build(
            builder.pull_request()
            .base_ref_name("main")
            .commit(
                builder.commit()
                .status(Commit.BUILD_SUCCESSFUL)
                .check_suites([builder.check_suite().check_runs([check_run])])
            )
        )
        pull_request_test = build(
            builder.pull_request()
            .base_ref_name("test")
            .commit(
                builder.commit()
                .status(Commit.BUILD_SUCCESSFUL)
                .check_suites([builder.check_suite().check_runs([check_run])])
            )
        )

        self.assertTrue(github_logic._maybe_rerun_stale_checks(pull_request_main))
        mock_rerequest_check_run.assert_called_once_with(
            pull_request_main.repository_owner_handle(),
            pull_request_main.repository_name(),
            check_run.database_id(),
        )
        mock_rerequest_check_run.reset_mock()

        self.assertTrue(github_logic._maybe_rerun_stale_checks(pull_request_test))
        mock_rerequest_check_run.assert_called_once_with(
            pull_request_test.repository_owner_handle(),
            pull_request_test.repository_name(),
            check_run.database_id(),
        )

    @patch("src.github.logic.SGTM_FEATURE__CHECK_RERUN_ON_APPROVAL_ENABLED", True)
    @patch("src.github.logic.SGTM_FEATURE__CHECK_RERUN_THRESHOLD_HOURS", 1)
    @patch(
        "src.github.logic.SGTM_FEATURE__CHECK_RERUN_BASE_REF_NAMES",
        ["main"],
    )
    def test_rerun_stale_checks_on_approved_pull_request(
        self, mock_rerequest_check_run
    ):
        check_run = build(builder.check_run().completed_at("2020-01-13T14:59:58Z"))
        pull_request = build(
            builder.pull_request()
            .base_ref_name("main")
            .commit(
                builder.commit()
                .status(Commit.BUILD_SUCCESSFUL)
                .check_suites([builder.check_suite().check_runs([check_run])])
            )
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.APPROVED)
            )
            .merged(False)
        )
        self.assertTrue(
            github_logic.maybe_rerun_stale_checks_on_approved_pull_request(pull_request)
        )
        mock_rerequest_check_run.assert_called_once_with(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            check_run.database_id(),
        )

    @patch("src.github.logic.SGTM_FEATURE__CHECK_RERUN_ON_APPROVAL_ENABLED", True)
    @patch("src.github.logic.SGTM_FEATURE__CHECK_RERUN_THRESHOLD_HOURS", 1)
    @patch(
        "src.github.logic.SGTM_FEATURE__CHECK_RERUN_BASE_REF_NAMES",
        ["main"],
    )
    def test_no_rerun_stale_checks_on_unapproved_pull_request(
        self, mock_rerequest_check_run
    ):
        check_run = build(builder.check_run().completed_at("2020-01-13T14:59:58Z"))
        pull_request = build(
            builder.pull_request()
            .base_ref_name("main")
            .commit(
                builder.commit()
                .status(Commit.BUILD_SUCCESSFUL)
                .check_suites([builder.check_suite().check_runs([check_run])])
            )
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.CHANGES_REQUESTED)
            )
            .merged(False)
        )
        self.assertFalse(
            github_logic.maybe_rerun_stale_checks_on_approved_pull_request(pull_request)
        )
        mock_rerequest_check_run.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__CHECK_RERUN_ON_APPROVAL_ENABLED", True)
    @patch("src.github.logic.SGTM_FEATURE__CHECK_RERUN_THRESHOLD_HOURS", 1)
    @patch(
        "src.github.logic.SGTM_FEATURE__CHECK_RERUN_BASE_REF_NAMES",
        ["main"],
    )
    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    @patch.object(github_client, "merge_pull_request")
    def test_rerun_stale_checks_on_automerge_pr(
        self, mock_merge_pull_request, mock_rerequest_check_run
    ):
        check_run = build(builder.check_run().completed_at("2020-01-13T14:59:58Z"))
        pull_request = build(
            builder.pull_request()
            .base_ref_name("main")
            .commit(
                builder.commit()
                .status(Commit.BUILD_SUCCESSFUL)
                .check_suites([builder.check_suite().check_runs([check_run])])
            )
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.APPROVED)
            )
            .label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
            .merged(False)
        )
        self.assertTrue(
            github_logic.maybe_rerun_stale_checks_on_approved_pull_request(pull_request)
        )
        mock_rerequest_check_run.assert_called_once_with(
            pull_request.repository_owner_handle(),
            pull_request.repository_name(),
            check_run.database_id(),
        )

        self.assertFalse(
            github_logic.maybe_automerge_pull_request_and_rerun_stale_checks(
                pull_request
            )
        )
        mock_merge_pull_request.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__CHECK_RERUN_ON_APPROVAL_ENABLED", True)
    @patch("src.github.logic.SGTM_FEATURE__CHECK_RERUN_THRESHOLD_HOURS", 1)
    @patch(
        "src.github.logic.SGTM_FEATURE__CHECK_RERUN_BASE_REF_NAMES",
        ["main"],
    )
    def test_no_rerun_when_check_run_not_complete(self, mock_rerequest_check_run):
        check_run = build(builder.check_run().completed_at(None))
        pull_request = build(
            builder.pull_request()
            .base_ref_name("main")
            .commit(
                builder.commit()
                .status(Commit.BUILD_SUCCESSFUL)
                .check_suites([builder.check_suite().check_runs([check_run])])
            )
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.APPROVED)
            )
            .merged(False)
        )
        self.assertFalse(
            github_logic.maybe_rerun_stale_checks_on_approved_pull_request(pull_request)
        )
        mock_rerequest_check_run.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__CHECK_RERUN_ON_APPROVAL_ENABLED", False)
    def test_noop_if_feature_not_enabled(self, mock_rerequest_check_run):
        check_run = build(builder.check_run().completed_at("2020-01-13T14:59:58Z"))
        pull_request = build(
            builder.pull_request()
            .base_ref_name("main")
            .commit(
                builder.commit()
                .status(Commit.BUILD_SUCCESSFUL)
                .check_suites([builder.check_suite().check_runs([check_run])])
            )
            .review(
                builder.review()
                .submitted_at("2020-01-13T14:59:58Z")
                .state(ReviewState.APPROVED)
            )
            .merged(False)
        )
        self.assertFalse(
            github_logic.maybe_rerun_stale_checks_on_approved_pull_request(pull_request)
        )
        mock_rerequest_check_run.assert_not_called()


@patch.object(github_client, "edit_pr_title")
@patch.object(github_client, "add_pr_comment")
class TestMaybeAddAutomergeWarningTitleAndComment(unittest.TestCase):
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
        for label, automerge_comment in [
            (
                github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value,
                github_logic.AUTOMERGE_COMMENT_WARNING_AFTER_TESTS_AND_APPROVAL,
            ),
            (
                github_logic.AutomergeLabel.AFTER_APPROVAL.value,
                github_logic.AUTOMERGE_COMMENT_WARNING_AFTER_APPROVAL,
            ),
        ]:
            pull_request = build(
                builder.pull_request()
                .title(self.SAMPLE_PR_TITLE)
                .label(builder.label().name(label))
            )

            github_logic.maybe_add_automerge_warning_comment(pull_request)

            add_pr_comment_mock.assert_called_with(
                pull_request.repository_owner_handle(),
                pull_request.repository_name(),
                pull_request.number(),
                automerge_comment,
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
                    .body(
                        github_logic.AUTOMERGE_COMMENT_WARNING_AFTER_TESTS_AND_APPROVAL
                    )
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
