import src.asana.helpers
from src.github.models import ReviewState
from test.impl.mock_dynamodb_test_case import MockDynamoDbTestCase
from test.impl.builders import builder, build


class BaseClass(MockDynamoDbTestCase):
    @classmethod
    def setUpClass(cls):
        MockDynamoDbTestCase.setUpClass()
        cls.test_data.insert_user_into_user_table(
            "github_test_user_login", "TEST_USER_ASANA_DOMAIN_USER_ID"
        )


class TestExtractsMiscellaneousFieldsFromPullRequest(BaseClass):
    def test_name(self):
        pull_request = build(
            builder.pull_request().number("PR_NUMBER").title("PR_TITLE")
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual("#PR_NUMBER - PR_TITLE", task_fields["name"])

    def test_html_body(self):
        pull_request = build(
            builder.pull_request()
            .author(builder.user("github_test_user_login"))
            .url("https://foo.bar/baz")
            .body("BODY")
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        actual = task_fields["html_notes"]
        expected_strings = [
            "<body>",
            "<em>",
            "This is a one-way sync from GitHub to Asana. Do not edit this task or comment on it!",
            "</em>",
            "\uD83D\uDD17",
            '<a href="https://foo.bar/baz">https://foo.bar/baz</a>',
            "✍",
            "TEST_USER_ASANA_DOMAIN_USER_ID",
            "<strong>",
            "Description:",
            "</strong>",
            "BODY",
            "</body>",
        ]
        self.assertContainsStrings(actual, expected_strings)


class TestExtractsAssigneeFromPullRequest(BaseClass):
    @classmethod
    def setUpClass(cls):
        BaseClass.setUpClass()
        cls.test_data.insert_user_into_user_table(
            "github_assignee_login_annie", "ANNIE_ASANA_DOMAIN_USER_ID"
        )
        cls.test_data.insert_user_into_user_table(
            "github_assignee_login_billy", "BILLY_ASANA_DOMAIN_USER_ID"
        )

    def test_assignee(self):
        pull_request = build(
            builder.pull_request().assignee(builder.user("github_test_user_login"))
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual("TEST_USER_ASANA_DOMAIN_USER_ID", task_fields["assignee"])

    def test_assignee_returns_first_assignee_by_login_if_many(self):
        pull_request = build(
            builder.pull_request().assignees(
                [
                    builder.user("github_assignee_login_billy"),
                    builder.user("github_assignee_login_annie"),
                ]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual("ANNIE_ASANA_DOMAIN_USER_ID", task_fields["assignee"])

    def test_assignee_returns_author_when_assignees_are_empty(self):
        pull_request = build(
            builder.pull_request().author(builder.user("github_test_user_login"))
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual("TEST_USER_ASANA_DOMAIN_USER_ID", task_fields["assignee"])


class TestExtractsCompletedStatusFromPullRequest(BaseClass):
    def test_completed_is_false_if_pr_is_not_closed_and_pr_is_not_merged(self):
        pull_request = build(builder.pull_request().closed(False).merged(False))
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(False, task_fields["completed"])

    def test_completed_is_true_if_pr_is_closed_but_pr_was_not_merged(self):
        pull_request = build(builder.pull_request().closed(True).merged(False))
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(True, task_fields["completed"])

    def test_completed_is_false_if_pr_is_closed_and_merged_but_not_reviewed(self):
        pull_request = build(builder.pull_request().closed(True).merged(True))
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(False, task_fields["completed"])

    def test_completed_is_true_if_pr_is_closed_and_pr_was_approved_before_merging(self):
        pull_request = build(
            builder.pull_request()
            .closed(True)
            .merged(False)
            .reviews(
                [
                    builder.review()
                    .submitted_at("2020-01-13T14:59:58Z")
                    .state(ReviewState.APPROVED)
                ]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(True, task_fields["completed"])

    def test_completed_is_false_if_pr_is_closed_and_was_approved_before_merging_but_changes_were_then_requested(
        self,
    ):
        pull_request = build(
            builder.pull_request()
            .closed(True)
            .merged(True)
            .merged("2020-01-13T14:59:59Z")
            .reviews(
                [
                    (
                        builder.review()
                        .submitted_at("2020-01-13T14:59:57Z")
                        .state(ReviewState.APPROVED)
                    ),
                    (
                        builder.review()
                        .submitted_at("2020-01-13T14:59:58Z")
                        .state(ReviewState.CHANGES_REQUESTED)
                    ),
                ]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(False, task_fields["completed"])

    def test_completed_handles_gracefully_if_pr_is_closed_and_pr_was_approved_before_merging_with_merged_glitch(
        self,
    ):
        pull_request = build(
            builder.pull_request()
            .closed(True)
            .merged(False)
            .merged_at("2020-01-13T14:59:58Z")
            .reviews(
                [
                    builder.review()
                    .submitted_at("2020-01-13T14:59:59Z")
                    .state(ReviewState.APPROVED)
                ]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(True, task_fields["completed"])

    def test_completed_is_true_if_pr_is_closed_and_was_approved_before_merging_even_if_changes_had_been_requested(
        self,
    ):
        pull_request = build(
            builder.pull_request()
            .closed(True)
            .merged(True)
            .merged_at("2020-01-13T14:59:59Z")
            .reviews(
                [
                    (
                        builder.review()
                        .submitted_at("2020-01-13T14:59:57Z")
                        .state(ReviewState.CHANGES_REQUESTED)
                    ),
                    (
                        builder.review()
                        .submitted_at("2020-01-13T14:59:58Z")
                        .state(ReviewState.APPROVED)
                    ),
                ]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(True, task_fields["completed"])

    def test_completed_is_true_if_pr_was_merged_and_changes_requested_and_commented_lgtm_on_the_pr_after_merge(
        self,
    ):
        pull_request = build(
            builder.pull_request()
            .closed(True)
            .merged(True)
            .merged_at("2020-01-13T14:59:59Z")
            .reviews(
                [
                    builder.review()
                    .submitted_at("2020-01-13T14:59:57Z")
                    .state(ReviewState.CHANGES_REQUESTED)
                ]
            )
            .comments(
                [builder.comment().published_at("2020-02-02T12:12:12Z").body("LGTM!")]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(True, task_fields["completed"])

    def test_completed_is_false_if_pr_was_merged_and_changes_requested_and_commented_lgtm_on_the_pr_before_merge(
        self,
    ):
        pull_request = build(
            builder.pull_request()
            .closed(True)
            .merged(True)
            .merged_at("2020-01-13T14:59:59Z")
            .reviews(
                [
                    builder.review()
                    .submitted_at("2020-01-13T14:59:57Z")
                    .state(ReviewState.CHANGES_REQUESTED)
                ]
            )
            .comments(
                [builder.comment().published_at("2020-01-13T14:59:58Z").body("LGTM!")]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(False, task_fields["completed"])

    def test_completed_is_true_if_pr_was_merged_and_changes_requested_but_still_said_lgtm_in_review_after_merge(
        self,
    ):
        # this is a bit of a nuanced case. Here the reviewer has requested changes, but still said LGTM!, so we
        # interpret this as the reviewer trusting the author to make the changes requested without having to come
        # back to the reviewer and review that the changes were made
        pull_request = build(
            builder.pull_request()
            .closed(True)
            .merged(True)
            .merged_at("2020-01-13T14:59:59Z")
            .reviews(
                [
                    builder.review()
                    .submitted_at("2020-02-13T14:59:57Z")
                    .state(ReviewState.CHANGES_REQUESTED)
                    .body("LGTM!")
                ]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(True, task_fields["completed"])


class TestExtractsFollowersFromPullRequest(BaseClass):
    def test_author_is_a_follower(self):
        pull_request = build(
            builder.pull_request().author(builder.user("github_test_user_login"))
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertIn("TEST_USER_ASANA_DOMAIN_USER_ID", task_fields["followers"])

    def test_assignee_is_a_follower(self):
        pull_request = build(
            builder.pull_request().assignee(
                builder.user("github_test_user_login", "TEST_USER_ASANA_DOMAIN_USER_ID")
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertIn("TEST_USER_ASANA_DOMAIN_USER_ID", task_fields["followers"])

    def test_reviewer_is_a_follower(self):
        pull_request = build(
            builder.pull_request().reviews(
                [
                    builder.review()
                    .submitted_at("2020-02-13T14:59:57Z")
                    .state(ReviewState.CHANGES_REQUESTED)
                    .body("LGTM!")
                    .author(builder.user("github_test_user_login"))
                ]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertIn("TEST_USER_ASANA_DOMAIN_USER_ID", task_fields["followers"])

    def test_commentor_is_a_follower(self):
        pull_request = build(
            builder.pull_request().comments(
                [
                    builder.comment()
                    .published_at("2020-01-13T14:59:58Z")
                    .body("LGTM!")
                    .author(builder.user("github_test_user_login"))
                ]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertIn("TEST_USER_ASANA_DOMAIN_USER_ID", task_fields["followers"])

    def test_requested_reviewer_is_a_follower(self):
        pull_request = build(
            builder.pull_request()
            .comments(
                [builder.comment().published_at("2020-01-13T14:59:58Z").body("LGTM!"),]
            )
            .requested_reviewers([builder.user("github_test_user_login")])
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertIn("TEST_USER_ASANA_DOMAIN_USER_ID", task_fields["followers"])

    def test_individual_that_is_at_mentioned_in_comments_is_a_follower(self):
        pull_request = build(
            builder.pull_request().comments(
                [builder.comment().body("@github_test_user_login")]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertIn("TEST_USER_ASANA_DOMAIN_USER_ID", task_fields["followers"])

    def test_individual_that_is_at_mentioned_in_review_comments_is_a_follower(self):
        pull_request = build(
            builder.pull_request().reviews(
                [builder.review().body("@github_test_user_login")]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertIn("TEST_USER_ASANA_DOMAIN_USER_ID", task_fields["followers"])

    def test_individual_that_is_at_mentioned_in_pr_body_is_a_follower(self):
        pull_request = build(builder.pull_request().body("@github_test_user_login"))
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertIn("TEST_USER_ASANA_DOMAIN_USER_ID", task_fields["followers"])

    def test_non_asana_user_is_not_a_follower(self):
        unknown_github_user = build(
            builder.user("github_unknown_user_login", "GITHUB_UNKNOWN_USER_NAME")
        )
        pull_request = build(
            builder.pull_request()
            .body("@github_unknown_user_login")
            .author(unknown_github_user)
            .assignee(unknown_github_user)
            .review(
                builder.review()
                .body("@github_unknown_user_login")
                .author(unknown_github_user)
            )
            .comment(
                builder.comment()
                .body("@github_unknown_user_login")
                .author(unknown_github_user)
            )
            .requested_reviewer(unknown_github_user)
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(0, len(task_fields["followers"]))


class TestExtractsInconsistentFieldsFromPullRequest(BaseClass):
    """
        This test case asserts that our behaviour is properly defined, even when some of our assumptions about GitHub
        are proven to be broken.
    """

    def test_does_not_care_about_merged_at_even_if_it_is_illegal_if_merged_is_false(
        self,
    ):
        def illegal_value_that_will_be_ignored():
            # merged_at is supposed to be a datetime, which will be compared with other datetime values,
            # so the Python interpreter should be massively unhappy if merged_at is touched and turns out
            # to be a function (i.e. because it is illegal to compare a function to a datetime with an ordering
            # operator such as < > <= >=)
            pass

        pull_request = build(
            builder.pull_request()
            .closed(True)
            .merged(False)
            .merged_at(illegal_value_that_will_be_ignored)
            .reviews(
                [
                    builder.review()
                    .submitted_at("2020-01-13T14:59:58Z")
                    .state(ReviewState.APPROVED)
                ]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(True, task_fields["completed"])

    def test_completed_is_false_if_pr_is_not_closed_but_still_merged(self):
        # this should be a totally illegal state that we received from GitHub, but it could theoretically exist due
        # to poorly implemented failure modes, concurrency issues, or data corruption due to errors
        pull_request = build(builder.pull_request().closed(False).merged(True))
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(False, task_fields["completed"])

    def test_does_not_rely_on_github_to_return_reviews_sorted_by_submitted_at_timestamp(
        self,
    ):
        # this would be a plausible state during a race condition, as two simultaneously submitted reviews could be
        # returned by github in the order they were inserted in a database, yet have slightly out-of-order timestamps
        pull_request = build(
            builder.pull_request()
            .closed(True)
            .merged(True)
            .merged_at("2020-01-13T14:59:59Z")
            .reviews(
                [
                    (
                        builder.review()
                        .submitted_at("2020-01-13T14:59:58Z")
                        .state(ReviewState.CHANGES_REQUESTED)
                    ),
                    (
                        builder.review()
                        .submitted_at("2020-01-13T14:59:57Z")
                        .state(ReviewState.APPROVED)
                    ),
                ]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(False, task_fields["completed"])
        pull_request = build(
            builder.pull_request()
            .closed(True)
            .merged(True)
            .merged_at("2020-01-13T14:59:59Z")
            .reviews(
                [
                    (
                        builder.review()
                        .submitted_at("2020-01-13T14:59:58Z")
                        .state(ReviewState.APPROVED)
                    ),
                    (
                        builder.review()
                        .submitted_at("2020-01-13T14:59:57Z")
                        .state(ReviewState.CHANGES_REQUESTED)
                    ),
                ]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(True, task_fields["completed"])


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
