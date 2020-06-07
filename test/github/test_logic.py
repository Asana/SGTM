import unittest
from datetime import datetime, timedelta
import src.github.logic as github_logic
from src.github.models import Review, ReviewState
from test.impl.builders import builder, build


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
