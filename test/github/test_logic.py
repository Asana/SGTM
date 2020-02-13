import unittest
from datetime import datetime, timedelta
import src.github.logic as github_logic
from src.github.models import Review
from test.github.helpers import (
    PullRequestBuilder,
    ReviewBuilder,
    CommentBuilder,
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
        self.assertEqual(github_logic._extract_mentions("hello @there"), ["there"])
        self.assertEqual(github_logic._extract_mentions("@hello there"), ["hello"])
        self.assertEqual(
            github_logic._extract_mentions("@hello @to-all123 there"),
            ["hello", "to-all123"],
        )
        self.assertEqual(github_logic._extract_mentions("hello @*"), [])

    def test_pull_request_comment_mentions(self):
        pull_request = (
            PullRequestBuilder()
            .with_comments(
                [
                    CommentBuilder(""),
                    CommentBuilder("@one @two @three"),
                    CommentBuilder("@four"),
                ]
            )
            .build()
        )
        self.assertEqual(
            github_logic._pull_request_comment_mentions(pull_request),
            ["one", "two", "three", "four"],
        )

    def test_pull_request_review_mentions(self):
        pull_request = (
            PullRequestBuilder()
            .with_reviews(
                [
                    ReviewBuilder("").with_comments(
                        [CommentBuilder("@one @two @three"), CommentBuilder("@four"),]
                    ),
                    ReviewBuilder("@a @b @c").with_comments(
                        [CommentBuilder(""), CommentBuilder("@five"),]
                    ),
                ]
            )
            .build()
        )
        self.assertEqual(
            sorted(github_logic._pull_request_review_mentions(pull_request)),
            ["a", "b", "c", "five", "four", "one", "three", "two"],
        )

    def test_pull_request_body_mentions(self):
        pull_request = PullRequestBuilder("@foo\n@bar").build()
        self.assertEqual(
            github_logic._pull_request_body_mentions(pull_request), ["foo", "bar"]
        )

    def test_pull_request_commenters(self):
        pull_request = (
            PullRequestBuilder()
            .with_comments(
                [
                    CommentBuilder().with_author(login="foo"),
                    CommentBuilder().with_author(login="bar"),
                ]
            )
            .build()
        )
        self.assertEqual(
            github_logic._pull_request_commenters(pull_request),
            ["bar", "foo"],  # sorted
        )

    def test_pull_request_approved_before_merging_review_approved_after_merge(self):
        merged_at = datetime.now()
        submitted_at = merged_at + timedelta(hours=1)

        pull_request = (
            PullRequestBuilder()
            .with_reviews(
                [
                    ReviewBuilder()
                    .with_submitted_at(submitted_at)
                    .with_state(Review.STATE_APPROVED)
                ]
            )
            .with_merged_at(merged_at)
            .build()
        )
        self.assertFalse(
            github_logic.pull_request_approved_before_merging(pull_request)
        )

    def test_pull_request_approved_before_merging_review_approved_before_merge(self):
        merged_at = datetime.now()
        submitted_at = merged_at - timedelta(hours=1)

        pull_request = (
            PullRequestBuilder()
            .with_reviews(
                [
                    ReviewBuilder()
                    .with_submitted_at(submitted_at)
                    .with_state(Review.STATE_APPROVED)
                ]
            )
            .with_merged_at(merged_at)
            .build()
        )
        self.assertTrue(github_logic.pull_request_approved_before_merging(pull_request))

    def test_pull_request_approved_before_merging_review_requested_changes_before_merge(
        self,
    ):
        merged_at = datetime.now()
        submitted_at = merged_at - timedelta(hours=1)

        pull_request = (
            PullRequestBuilder()
            .with_reviews(
                [
                    ReviewBuilder()
                    .with_submitted_at(submitted_at)
                    .with_state(Review.STATE_CHANGES_REQUESTED)
                ]
            )
            .with_merged_at(merged_at)
            .build()
        )
        self.assertFalse(
            github_logic.pull_request_approved_before_merging(pull_request)
        )

    def test_pull_request_approved_before_merging_no_reviews(self):
        pull_request = PullRequestBuilder().with_merged_at(datetime.now()).build()
        self.assertFalse(
            github_logic.pull_request_approved_before_merging(pull_request)
        )

    def test_pull_request_approved_after_merging_no_reviews_or_comments(self):
        pull_request = PullRequestBuilder().with_merged_at(datetime.now()).build()
        self.assertFalse(github_logic.pull_request_approved_after_merging(pull_request))

    def test_pull_request_approved_after_merging_reviews_and_comments_no_approvals(
        self,
    ):
        # The PR has reviews and comments, but neither have approval messages

        merged_at = datetime.now()
        reviewed_at = merged_at + timedelta(days=1)
        commented_at = merged_at + timedelta(days=2)
        pull_request = (
            PullRequestBuilder()
            .with_merged_at(datetime.now())
            .with_reviews(
                [ReviewBuilder("This looks OK").with_submitted_at(reviewed_at)]
            )
            .with_comments(
                [CommentBuilder("v cool use of emojis").with_created_at(commented_at)]
            )
            .build()
        )
        self.assertFalse(github_logic.pull_request_approved_after_merging(pull_request))

    def test_pull_request_approved_after_merging_review_with_approval(self):
        merged_at = datetime.now()
        reviewed_at = merged_at + timedelta(days=1)
        commented_at = merged_at + timedelta(days=2)
        pull_request = (
            PullRequestBuilder()
            .with_merged_at(datetime.now())
            .with_reviews(
                [ReviewBuilder("This looks OK").with_submitted_at(reviewed_at)]
            )
            .with_comments([CommentBuilder("LGTM!").with_created_at(commented_at)])
            .build()
        )
        self.assertTrue(github_logic.pull_request_approved_after_merging(pull_request))

    def test_pull_request_approved_after_merging_comment_with_approval(self):
        merged_at = datetime.now()
        reviewed_at = merged_at + timedelta(days=1)
        commented_at = merged_at + timedelta(days=2)
        pull_request = (
            PullRequestBuilder()
            .with_merged_at(datetime.now())
            .with_reviews(
                [ReviewBuilder("This looks great! :+1:").with_submitted_at(reviewed_at)]
            )
            .with_comments(
                [CommentBuilder("v cool use of emojis").with_created_at(commented_at)]
            )
            .build()
        )
        self.assertTrue(github_logic.pull_request_approved_after_merging(pull_request))


if __name__ == '__main__':
    unittest.main()