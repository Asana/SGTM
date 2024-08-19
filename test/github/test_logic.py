import unittest
from unittest.mock import patch

import src.github.client as github_client
import src.github.logic as github_logic
from src.github.models import Commit, ReviewState, MergeableState
from test.impl.builders import builder, build


@patch.object(github_client, "merge_pull_request")
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
        self.assertTrue(github_logic.maybe_automerge_pull_request(pull_request))
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
        self.assertTrue(github_logic.maybe_automerge_pull_request(pull_request))
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
        self.assertTrue(github_logic.maybe_automerge_pull_request(pull_request))
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
        self.assertTrue(github_logic.maybe_automerge_pull_request(pull_request))
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
        self.assertFalse(github_logic.maybe_automerge_pull_request(pull_request))
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
        self.assertFalse(github_logic.maybe_automerge_pull_request(pull_request))
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
        self.assertFalse(github_logic.maybe_automerge_pull_request(pull_request))
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
        self.assertFalse(github_logic.maybe_automerge_pull_request(pull_request))
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
        self.assertFalse(github_logic.maybe_automerge_pull_request(pull_request))
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
        self.assertFalse(github_logic.maybe_automerge_pull_request(pull_request))
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
        self.assertFalse(github_logic.maybe_automerge_pull_request(pull_request))
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
        self.assertFalse(github_logic.maybe_automerge_pull_request(pull_request))
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
        self.assertTrue(github_logic.maybe_automerge_pull_request(pull_request))
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
        self.assertTrue(github_logic.maybe_automerge_pull_request(pull_request))
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
        self.assertFalse(github_logic.maybe_automerge_pull_request(pull_request))
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
        self.assertTrue(github_logic.maybe_automerge_pull_request(pull_request))
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
        self.assertFalse(github_logic.maybe_automerge_pull_request(pull_request))
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
        self.assertFalse(github_logic.maybe_automerge_pull_request(pull_request))
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
        self.assertFalse(github_logic.maybe_automerge_pull_request(pull_request))
        mock_merge_pull_request.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_when_in_merge_queue(
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
            .isInMergeQueue(True)
            .mergeable(MergeableState.MERGEABLE)
            .merged(False)
            .label(builder.label().name(github_logic.AutomergeLabel.AFTER_TESTS.value))
        )
        self.assertFalse(github_logic.maybe_automerge_pull_request(pull_request))
        mock_merge_pull_request.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_is_pull_request_ready_for_automerge_with_open_prs(
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
            .base_ref_associated_pull_requests(1)
            .mergeable(MergeableState.MERGEABLE)
            .merged(False)
            .label(builder.label().name(github_logic.AutomergeLabel.AFTER_TESTS.value))
        )
        self.assertFalse(github_logic.maybe_automerge_pull_request(pull_request))
        mock_merge_pull_request.assert_not_called()


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
                owner=pull_request.repository_owner_handle(),
                repository=pull_request.repository_name(),
                number=pull_request.number(),
                comment=automerge_comment,
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
    def test_adds_automerge_warning_comment_if_open_prs(
        self, add_pr_comment_mock, edit_pr_title_mock
    ):
        pull_request = build(
            builder.pull_request()
            .title(self.SAMPLE_PR_TITLE)
            .label(builder.label().name(github_logic.AutomergeLabel.AFTER_TESTS.value))
            .base_ref_associated_pull_requests(1)
        )

        github_logic.maybe_add_automerge_warning_comment(pull_request)

        add_pr_comment_mock.assert_called_with(
            owner=pull_request.repository_owner_handle(),
            repository=pull_request.repository_name(),
            number=pull_request.number(),
            comment=github_logic.AUTOMERGE_COMMENT_WARNING_OPEN_BASE_REF_PRS,
        )

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_does_not_add_warning_comment_for_open_prs_if_no_label(
        self, add_pr_comment_mock, edit_pr_title_mock
    ):
        pull_request = build(
            builder.pull_request()
            .base_ref_associated_pull_requests(1)
            .title(self.SAMPLE_PR_TITLE)
        )

        github_logic.maybe_add_automerge_warning_comment(pull_request)

        add_pr_comment_mock.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_does_not_add_warning_comment_for_closed_prs(
        self, add_pr_comment_mock, edit_pr_title_mock
    ):
        pull_request = build(
            builder.pull_request()
            .title(self.SAMPLE_PR_TITLE)
            .label(builder.label().name(github_logic.AutomergeLabel.AFTER_TESTS.value))
            .base_ref_associated_pull_requests(1)
            .closed(True)
        )

        github_logic.maybe_add_automerge_warning_comment(pull_request)

        add_pr_comment_mock.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_does_not_add_warning_comment_for_merged_prs(
        self, add_pr_comment_mock, edit_pr_title_mock
    ):
        pull_request = build(
            builder.pull_request()
            .title(self.SAMPLE_PR_TITLE)
            .label(builder.label().name(github_logic.AutomergeLabel.AFTER_TESTS.value))
            .base_ref_associated_pull_requests(1)
            .merged(True)
        )

        github_logic.maybe_add_automerge_warning_comment(pull_request)

        add_pr_comment_mock.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_does_not_add_warning_comment_for_approved_prs(
        self, add_pr_comment_mock, edit_pr_title_mock
    ):
        review = build(
            builder.review()
            .state(ReviewState.APPROVED)
        )
        pull_request = build(
            builder.pull_request()
            .title(self.SAMPLE_PR_TITLE)
            .label(builder.label().name(github_logic.AutomergeLabel.AFTER_TESTS.value))
            .base_ref_associated_pull_requests(1)
            .reviews([review])
        )

        github_logic.maybe_add_automerge_warning_comment(pull_request)

        add_pr_comment_mock.assert_not_called()

    @patch("src.github.logic.SGTM_FEATURE__AUTOMERGE_ENABLED", True)
    def test_adds_multiple_comments_if_changed_state(
        self, add_pr_comment_mock, edit_pr_title_mock
    ):
        pull_request_builder = (
            builder.pull_request()
            .title(self.SAMPLE_PR_TITLE)
            .label(
                builder.label().name(
                    github_logic.AutomergeLabel.AFTER_TESTS_AND_APPROVAL.value
                )
            )
            .base_ref_associated_pull_requests(1)
        )

        def mock_add_pr_comment(owner: str, repository: str, number: int, comment: str):
            nonlocal pull_request_builder
            pull_request_builder = pull_request_builder.comment(
                builder.comment(body=comment)
            )

        add_pr_comment_mock.side_effect = mock_add_pr_comment

        github_logic.maybe_add_automerge_warning_comment(build(pull_request_builder))

        self.assertEqual(
            build(pull_request_builder).to_raw()["comments"]["nodes"][0]["body"],
            github_logic.AUTOMERGE_COMMENT_WARNING_OPEN_BASE_REF_PRS,
        )

        pull_request_builder = pull_request_builder.base_ref_associated_pull_requests(0)
        github_logic.maybe_add_automerge_warning_comment(build(pull_request_builder))

        self.assertEqual(
            len(build(pull_request_builder).to_raw()["comments"]["nodes"]), 2
        )
        self.assertEqual(
            build(pull_request_builder).to_raw()["comments"]["nodes"][0]["body"],
            github_logic.AUTOMERGE_COMMENT_WARNING_OPEN_BASE_REF_PRS,
        )
        self.assertEqual(
            build(pull_request_builder).to_raw()["comments"]["nodes"][1]["body"],
            github_logic.AUTOMERGE_COMMENT_WARNING_AFTER_TESTS_AND_APPROVAL,
        )


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
