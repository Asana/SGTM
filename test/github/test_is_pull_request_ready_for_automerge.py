import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
import src.github.logic as github_logic
from src.github.models import Commit, ReviewState, PullRequest, MergeableState
from test.impl.builders import builder, build
import src.github.controller as github_controller
import src.github.client as github_client


@patch("os.getenv")
class TestIsPullRequestReadyForAutomerge(unittest.TestCase):
    def test_is_pull_request_ready_for_automerge_after_tests_and_approval(
        self, get_env_mock
    ):
        get_env_mock.return_value = "true"
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
        self.assertTrue(github_logic._is_pull_request_ready_for_automerge(pull_request))

    def test_is_pull_request_ready_for_automerge_after_tests(self, get_env_mock):
        get_env_mock.return_value = "true"
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
        self.assertTrue(github_logic._is_pull_request_ready_for_automerge(pull_request))

    def test_is_pull_request_ready_for_automerge_immediately(self, get_env_mock):
        get_env_mock.return_value = "true"
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
        self.assertTrue(github_logic._is_pull_request_ready_for_automerge(pull_request))

    def test_is_pull_request_ready_for_automerge_immediately_conflicting(
        self, get_env_mock
    ):
        get_env_mock.return_value = "true"
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
            github_logic._is_pull_request_ready_for_automerge(pull_request)
        )

    def test_is_pull_request_ready_for_automerge_autofail_if_no_env_variable(
        self, get_env_mock
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
            github_logic._is_pull_request_ready_for_automerge(pull_request)
        )

    def test_is_pull_request_ready_for_automerge_autofail_if_merged(self, get_env_mock):
        get_env_mock.return_value = "true"
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
            github_logic._is_pull_request_ready_for_automerge(pull_request)
        )

    def test_is_pull_request_ready_for_automerge_autofail_if_closed(self, get_env_mock):
        get_env_mock.return_value = "true"
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
            github_logic._is_pull_request_ready_for_automerge(pull_request)
        )

    def test_is_pull_request_ready_for_automerge_build_failed(self, get_env_mock):
        get_env_mock.return_value = "true"
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
            github_logic._is_pull_request_ready_for_automerge(pull_request)
        )

    def test_is_pull_request_ready_for_automerge_build_pending(self, get_env_mock):
        get_env_mock.return_value = "true"
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
            github_logic._is_pull_request_ready_for_automerge(pull_request)
        )

    def test_is_pull_request_ready_for_automerge_after_approval_reviewer_requested_changes(
        self, get_env_mock
    ):
        get_env_mock.return_value = "true"
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
            github_logic._is_pull_request_ready_for_automerge(pull_request)
        )

    def test_is_pull_request_ready_for_automerge_after_approval_approved_and_requested_changes(
        self, get_env_mock
    ):
        get_env_mock.return_value = "true"
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
        self.assertFalse(
            github_logic._is_pull_request_ready_for_automerge(pull_request)
        )

    def test_is_pull_request_ready_for_automerge_changes_after_approval_requested_then_approval(
        self, get_env_mock
    ):
        get_env_mock.return_value = "true"
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
        self.assertTrue(github_logic._is_pull_request_ready_for_automerge(pull_request))

    def test_is_pull_request_ready_for_automerge_after_tests_no_review(
        self, get_env_mock
    ):
        get_env_mock.return_value = "true"
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
            github_logic._is_pull_request_ready_for_automerge(pull_request)
        )

    def test_is_pull_request_ready_for_automerge_after_approval_no_review(
        self, get_env_mock
    ):
        get_env_mock.return_value = "true"
        pull_request = build(
            builder.pull_request()
            .commit(builder.commit().status(Commit.BUILD_SUCCESSFUL))
            .title("blah blah [shipit]")
            .mergeable(MergeableState.MERGEABLE)
            .merged(False)
            .label(builder.label().name(github_logic.AutomergeLabel.AFTER_TESTS.value))
        )
        self.assertTrue(github_logic._is_pull_request_ready_for_automerge(pull_request))

    def test_is_pull_request_ready_for_automerge_no_automerge_label(self, get_env_mock):
        get_env_mock.return_value = "true"
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
            github_logic._is_pull_request_ready_for_automerge(pull_request)
        )

    def test_is_pull_request_ready_for_automerge_after_approval_mergeable_is_false(
        self, get_env_mock
    ):
        get_env_mock.return_value = "true"
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
            github_logic._is_pull_request_ready_for_automerge(pull_request)
        )

    def test_is_pull_request_ready_for_automerge_after_tests_mergeable_is_false(
        self, get_env_mock
    ):
        get_env_mock.return_value = "true"
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
            github_logic._is_pull_request_ready_for_automerge(pull_request)
        )


class GithubLogicTest(unittest.TestCase):
    def test_inject_asana_task_into_pull_request_body(self):
        task_url = "https://asana.com/task/1"
        self.assertEqual(
            github_logic.inject_asana_task_into_pull_request_body(
                "this is the original body", task_url
            ),
            f"this is the original body\n\n\nPull Request synchronized with [Asana task]({task_url})",
        )

    def test_extract_mentions(self):
        self.assertEqual(github_logic._extract_mentions("hello"), [])
        self.assertEqual(github_logic._extract_mentions("Hello @There"), ["There"])
        self.assertEqual(github_logic._extract_mentions("@hello there"), ["hello"])
        self.assertEqual(
            github_logic._extract_mentions("@hello @to-all123 there"),
            ["hello", "to-all123"],
        )
        self.assertEqual(github_logic._extract_mentions("hello @*"), [])

    def test_pull_request_comment_mentions(self):
        pull_request = build(
            builder.pull_request().comments(
                [
                    builder.comment(""),
                    builder.comment("@one @two @three"),
                    builder.comment("@four"),
                ]
            )
        )
        self.assertEqual(
            github_logic._pull_request_comment_mentions(pull_request),
            ["one", "two", "three", "four"],
        )

    def test_pull_request_review_mentions(self):
        pull_request = build(
            builder.pull_request().reviews(
                [
                    builder.review("").comments(
                        [builder.comment("@one @two @three"), builder.comment("@four"),]
                    ),
                    builder.review("@a @b @c").comments(
                        [builder.comment(""), builder.comment("@five"),]
                    ),
                ]
            )
        )
        self.assertEqual(
            sorted(github_logic._pull_request_review_mentions(pull_request)),
            ["a", "b", "c", "five", "four", "one", "three", "two"],
        )

    def test_pull_request_body_mentions(self):
        pull_request = builder.pull_request("@foo\n@bar").build()
        self.assertEqual(
            github_logic._pull_request_body_mentions(pull_request), ["foo", "bar"]
        )

    def test_pull_request_commenters(self):
        pull_request = build(
            builder.pull_request().comments(
                [
                    builder.comment().author(builder.user().login("foo")),
                    builder.comment().author(builder.user().login("bar")),
                ]
            )
        )
        self.assertEqual(
            github_logic._pull_request_commenters(pull_request),
            ["bar", "foo"],  # sorted
        )

    def test_pull_request_approved_before_merging_review_approved_after_merge(self):
        merged_at = datetime.now()
        submitted_at = merged_at + timedelta(hours=1)

        pull_request = build(
            builder.pull_request()
            .reviews(
                [
                    builder.review()
                    .submitted_at(submitted_at)
                    .state(ReviewState.APPROVED)
                ]
            )
            .merged_at(merged_at)
        )
        self.assertFalse(
            github_logic.pull_request_approved_before_merging(pull_request)
        )

    def test_pull_request_approved_before_merging_review_approved_before_merge(self):
        merged_at = datetime.now()
        submitted_at = merged_at - timedelta(hours=1)

        pull_request = build(
            builder.pull_request()
            .reviews(
                [
                    builder.review()
                    .submitted_at(submitted_at)
                    .state(ReviewState.APPROVED)
                ]
            )
            .merged_at(merged_at)
        )
        self.assertTrue(github_logic.pull_request_approved_before_merging(pull_request))

    def test_pull_request_approved_before_merging_review_requested_changes_before_merge(
        self,
    ):
        merged_at = datetime.now()
        submitted_at = merged_at - timedelta(hours=1)

        pull_request = build(
            builder.pull_request()
            .reviews(
                [
                    builder.review()
                    .submitted_at(submitted_at)
                    .state(ReviewState.CHANGES_REQUESTED)
                ]
            )
            .merged_at(merged_at)
        )
        self.assertFalse(
            github_logic.pull_request_approved_before_merging(pull_request)
        )

    def test_pull_request_approved_before_merging_no_reviews(self):
        pull_request = builder.pull_request().merged_at(datetime.now()).build()
        self.assertFalse(
            github_logic.pull_request_approved_before_merging(pull_request)
        )

    def test_pull_request_approved_after_merging_no_reviews_or_comments(self):
        pull_request = builder.pull_request().merged_at(datetime.now()).build()
        self.assertFalse(github_logic.pull_request_approved_after_merging(pull_request))

    def test_pull_request_approved_after_merging_reviews_and_comments_no_approvals(
        self,
    ):
        # The PR has reviews and comments, but neither have approval messages

        merged_at = datetime.now()
        reviewed_at = merged_at + timedelta(days=1)
        commented_at = merged_at + timedelta(days=2)
        pull_request = build(
            builder.pull_request()
            .merged_at(datetime.now())
            .reviews([builder.review("This looks OK").submitted_at(reviewed_at)])
            .comments(
                [builder.comment("v cool use of emojis").published_at(commented_at)]
            )
        )
        self.assertFalse(github_logic.pull_request_approved_after_merging(pull_request))

    def test_pull_request_approved_after_merging_review_that_had_approval(self):
        merged_at = datetime.now()
        reviewed_at = merged_at + timedelta(days=1)
        commented_at = merged_at + timedelta(days=2)
        pull_request = build(
            builder.pull_request()
            .merged_at(datetime.now())
            .reviews([builder.review("This looks OK").submitted_at(reviewed_at)])
            .comments([builder.comment("SGTM!").published_at(commented_at)])
        )
        self.assertTrue(github_logic.pull_request_approved_after_merging(pull_request))

    def test_pull_request_approved_after_merging_comment_that_had_approval(self):
        merged_at = datetime.now()
        reviewed_at = merged_at + timedelta(days=1)
        commented_at = merged_at + timedelta(days=2)
        pull_request = build(
            builder.pull_request()
            .merged_at(datetime.now())
            .reviews(
                [builder.review("This looks great! :+1:").submitted_at(reviewed_at)]
            )
            .comments(
                [builder.comment("v cool use of emojis").published_at(commented_at)]
            )
        )
        self.assertTrue(github_logic.pull_request_approved_after_merging(pull_request))


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
