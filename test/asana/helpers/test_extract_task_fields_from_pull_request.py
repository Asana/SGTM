import src.asana.helpers
from test.asana.helpers.base_class import BaseClass


class TestExtractsMiscellaneousFieldsFromPullRequest(BaseClass):

    def test_extracting_fields_from_pr_none_causes_a_valueerror(self):
        try:
            src.asana.helpers.extract_task_fields_from_pull_request(None)
            self.fail("This code should have been unreachable")
        except ValueError:
            pass

    def test_name(self):
        pull_request = create_pull_request(number="PR_NUMBER", title="PR_TITLE")
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual("#PR_NUMBER - PR_TITLE", task_fields["name"])

    def test_html_body(self):
        pull_request = create_pull_request(url="https://foo.bar/baz", body="BODY")
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        actual = task_fields["html_notes"]
        expected_strings = [
            "<body>",
            "<em>",
            "This is a one-way sync from GitHub to Asana. Do not edit this task or comment on it!",
            "</em>",
            "\uD83D\uDD17",
            "https://foo.bar/baz",
            "✍",
            "AUTHOR_ASANA_DOMAIN_USER_ID",
            "<strong>",
            "Description:",
            "</strong>",
            "BODY",
            "</body>"
        ]
        for expected in expected_strings:
            self.assertIn(expected, actual, f"Expected html_notes to contain {expected}")


class TestExtractsAssigneeFromPullRequest(BaseClass):

    def test_assignee(self):
        assignee_nodes = [{"login": "github_assignee_login"}]
        pull_request = create_pull_request(assignees={"nodes": assignee_nodes})
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual("ASSIGNEE_ASANA_DOMAIN_USER_ID", task_fields["assignee"])

    def test_assignee_returns_first_assignee_by_login_if_many(self):
        assignee_nodes = [{"login": "github_assignee_login_billy"}, {"login": "github_assignee_login_annie"}]
        pull_request = create_pull_request(assignees={"nodes": assignee_nodes})
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual("ANNIE_ASANA_DOMAIN_USER_ID", task_fields["assignee"])

    def test_assignee_returns_author_when_assignees_are_empty(self):
        pull_request = create_pull_request()
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual("AUTHOR_ASANA_DOMAIN_USER_ID", task_fields["assignee"])


class TestExtractsCompletedStatusFromPullRequest(BaseClass):

    def test_completed_is_false_if_pr_is_not_closed_and_pr_is_not_merged(self):
        pull_request = create_pull_request(closed=False, merged=False)
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual(False, task_fields["completed"])

    def test_completed_is_true_if_pr_is_closed_but_pr_was_not_merged(self):
        pull_request = create_pull_request(closed=True, merged=False)
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual(True, task_fields["completed"])

    def test_completed_is_false_if_pr_is_closed_and_merged_but_not_reviewed(self):
        pull_request = create_pull_request(closed=True, merged=True)
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual(False, task_fields["completed"])

    def test_completed_is_true_if_pr_is_closed_and_pr_was_approved_before_merging(self):
        pull_request = create_pull_request(
            closed=True, merged=False, with_reviews=[
                create_review(submitted_at="2020-01-13T14:59:58Z", state="APPROVED")
            ])
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual(True, task_fields["completed"])

    def test_completed_is_false_if_pr_is_closed_and_was_approved_before_merging_but_changes_were_then_requested(self):
        pull_request = create_pull_request(
            closed=True, merged=True, merged_at="2020-01-13T14:59:59Z", with_reviews=[
                create_review(submitted_at="2020-01-13T14:59:57Z", state="APPROVED"),
                create_review(submitted_at="2020-01-13T14:59:58Z", state="CHANGES_REQUESTED"),
            ])
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual(False, task_fields["completed"])

    def test_completed_is_true_if_pr_is_closed_and_pr_was_approved_before_merging(self):
        pull_request = create_pull_request(
            closed=True, merged=False, merged_at="2020-01-13T14:59:58Z", with_reviews=[
                create_review(submitted_at="2020-01-13T14:59:59Z", state="APPROVED")
            ])
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual(True, task_fields["completed"])

    def test_completed_is_true_if_pr_is_closed_and_was_approved_before_merging_even_if_changes_had_been_requested(self):
        pull_request = create_pull_request(
            closed=True, merged=True, merged_at="2020-01-13T14:59:59Z", with_reviews=[
                create_review(submitted_at="2020-01-13T14:59:57Z", state="CHANGES_REQUESTED"),
                create_review(submitted_at="2020-01-13T14:59:58Z", state="APPROVED"),
            ])
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual(True, task_fields["completed"])

    def test_completed_is_true_if_pr_was_merged_with_changes_requested_and_commented_lgtm_on_the_pr_after_merge(self):
        pull_request = create_pull_request(
            closed=True, merged=True, merged_at="2020-01-13T14:59:59Z", with_reviews=[
                create_review(submitted_at="2020-01-13T14:59:57Z", state="CHANGES_REQUESTED"),
            ], with_comments=[
                create_comment(created_at="2020-02-02T12:12:12Z", body="LGTM!")
            ])
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual(True, task_fields["completed"])

    def test_completed_is_false_if_pr_was_merged_with_changes_requested_and_commented_lgtm_on_the_pr_before_merge(self):
        pull_request = create_pull_request(
            closed=True, merged=True, merged_at="2020-01-13T14:59:59Z", with_reviews=[
                create_review(submitted_at="2020-01-13T14:59:57Z", state="CHANGES_REQUESTED"),
            ], with_comments=[
                create_comment(created_at="2020-01-13T14:59:58Z", body="LGTM!")
            ])
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual(False, task_fields["completed"])

    def test_completed_is_true_if_pr_was_merged_with_changes_requested_but_still_said_lgtm_in_review_after_merge(self):
        # this is a bit of a nuanced case. Here the reviewer has requested changes, but still said LGTM!, so we
        # interpret this as the reviewer trusting the author to make the changes requested without having to come
        # back to the reviewer and review that the changes were made
        pull_request = create_pull_request(
            closed=True, merged=True, merged_at="2020-01-13T14:59:59Z", with_reviews=[
                create_review(submitted_at="2020-02-13T14:59:57Z", state="CHANGES_REQUESTED", body="LGTM!")
            ])
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual(True, task_fields["completed"])
        

class TestExtractsFollowersFromPullRequest(BaseClass):

    def test_author_is_a_follower(self):
        pull_request = create_pull_request()
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertIn("AUTHOR_ASANA_DOMAIN_USER_ID", task_fields["followers"])

    def test_assignee_is_a_follower(self):
        pull_request = create_pull_request(with_assignees=[
            create_github_user("github_assignee_login", "GITHUB_ASSIGNEE_NAME")
        ])
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertIn("ASSIGNEE_ASANA_DOMAIN_USER_ID", task_fields["followers"])

    def test_reviewer_is_a_follower(self):
        pull_request = create_pull_request(with_reviews=[create_review(
            submitted_at="2020-02-13T14:59:57Z",
            state="CHANGES_REQUESTED",
            body="LGTM!",
            with_author=create_github_user("github_reviewer_login")
        )])
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertIn("REVIEWER_ASANA_DOMAIN_USER_ID", task_fields["followers"])

    def test_commentor_is_a_follower(self):
        pull_request = create_pull_request(with_comments=[
            create_comment(created_at="2020-01-13T14:59:58Z", body="LGTM!",
                with_author=create_github_user("github_commentor_login"))
        ])
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertIn("COMMENTOR_ASANA_DOMAIN_USER_ID", task_fields["followers"])

    def test_requested_reviewer_is_a_follower(self):
        pull_request = create_pull_request(with_comments=[
            create_comment(created_at="2020-01-13T14:59:58Z", body="LGTM!"),
        ], with_requested_reviewers=[create_github_user("github_requested_reviewer_login")])
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertIn("REQUESTED_REVIEWER_ASANA_DOMAIN_USER_ID", task_fields["followers"])

    def test_individual_that_is_at_mentioned_in_comments_is_a_follower(self):
        pull_request = create_pull_request(with_comments=[create_comment(body="@github_at_mentioned_login")])
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertIn("AT_MENTIONED_ASANA_DOMAIN_USER_ID", task_fields["followers"])

    def test_individual_that_is_at_mentioned_in_review_comments_is_a_follower(self):
        pull_request = create_pull_request(with_reviews=[create_review(body="@github_at_mentioned_login")])
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertIn("AT_MENTIONED_ASANA_DOMAIN_USER_ID", task_fields["followers"])

    def test_individual_that_is_at_mentioned_in_pr_body_is_a_follower(self):
        pull_request = create_pull_request(with_body="@github_at_mentioned_login")
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertIn("AT_MENTIONED_ASANA_DOMAIN_USER_ID", task_fields["followers"])

    def test_non_asana_user_is_not_a_follower(self):
        unknown_github_user = create_github_user("github_unknown_user_login", "GITHUB_UNKNOWN_USER_NAME")
        pull_request = create_pull_request(
            with_body="@github_unknown_user_login",
            with_author=unknown_github_user,
            with_assignees=[unknown_github_user],
            with_reviews=[create_review(
                            body="@github_unknown_user_login",
                            with_author=unknown_github_user)],
            with_comments=[create_comment(
                            body="@github_unknown_user_login",
                            with_author=unknown_github_user)],
            with_requested_reviewers=[unknown_github_user],
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual(0, len(task_fields["followers"]))


class TestExtractsInconsistentFieldsFromPullRequest(BaseClass):
    """
        This test case asserts that our behaviour is properly defined, even when some of our assumptions about GitHub
        are proven to be broken.
    """

    def test_does_not_care_about_merged_at_even_if_it_is_illegal_if_merged_is_false(self):
        def illegal_value_that_will_be_ignored():
            # merged_at is supposed to be a datetime, which will be compared with other datetime values,
            # so the Python interpreter should be massively unhappy if merged_at is touched and turns out
            # to be a function (i.e. because it is illegal to compare a function to a datetime with an ordering
            # operator such as < > <= >=)
            pass
        pull_request = create_pull_request(
            closed=True, merged=False, merged_at=illegal_value_that_will_be_ignored, with_reviews=[
                create_review(submitted_at="2020-01-13T14:59:58Z", state="APPROVED")
            ])
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual(True, task_fields["completed"])

    def test_completed_is_false_if_pr_is_not_closed_but_still_merged(self):
        # this should be a totally illegal state that we received from GitHub, but it could theoretically exist due
        # to poorly implemented failure modes, concurrency issues, or data corruption due to errors
        pull_request = create_pull_request(closed=False, merged=True)
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual(False, task_fields["completed"])

    def test_does_not_rely_on_github_to_return_reviews_sorted_by_created_at_timestamp(self):
        # this would be a plausible state during a race condition, as two simultaneously submitted reviews could be
        # returned by github in the order they were inserted in a database, yet have slightly out-of-order timestamps
        pull_request = create_pull_request(
            closed=True, merged=True, merged_at="2020-01-13T14:59:59Z", with_reviews=[
                create_review(submitted_at="2020-01-13T14:59:58Z", state="CHANGES_REQUESTED"),
                create_review(submitted_at="2020-01-13T14:59:57Z", state="APPROVED"),
            ])
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual(False, task_fields["completed"])

        pull_request = create_pull_request(
            closed=True, merged=True, merged_at="2020-01-13T14:59:59Z", with_reviews=[
                create_review(submitted_at="2020-01-13T14:59:58Z", state="APPROVED"),
                create_review(submitted_at="2020-01-13T14:59:57Z", state="CHANGES_REQUESTED"),
            ])
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual(True, task_fields["completed"])


def create_github_user(login, name = None):
    return login, name


def create_comment(**keywords):
    from test.github.helpers import CommentBuilder
    builder = CommentBuilder()
    for k, v in keywords.items():
        builder.raw_comment[k] = v
    if "with_author" in keywords:
        login, name = keywords["with_author"]
        builder = builder.with_author(login, name)
    return builder.build()


def create_review(**keywords):
    from test.github.helpers import ReviewBuilder
    builder = ReviewBuilder()
    for k, v in keywords.items():
        if not k.startswith("with_"):
            builder.raw_review[k] = v
    if "with_comments" in keywords:
        builder = builder.with_comments(keywords["with_comments"])
    if "with_author" in keywords:
        login, name = keywords["with_author"]
        builder = builder.with_author(login, name)
    return builder.build()


def create_pull_request(**keywords):
    from test.github.helpers import PullRequestBuilder
    builder = PullRequestBuilder()
    for k, v in keywords.items():
        if not k.startswith("with_"):
            builder.raw_pr[k] = v
    if "with_author" in keywords:
        login, name = keywords["with_author"]
        builder = builder.with_author(login, name)
    else:
        builder = builder.with_author("github_author_login", "GITHUB_AUTHOR_NAME")
    if "with_body" in keywords:
        builder = builder.with_body(keywords["with_body"])
    if "with_reviews" in keywords:
        builder = builder.with_reviews(keywords["with_reviews"])
    if "with_comments" in keywords:
        builder = builder.with_comments(keywords["with_comments"])
    if "with_assignees" in keywords:
        builder = builder.with_assignees(keywords["with_assignees"])
    if "with_requested_reviewers" in keywords:
        builder = builder.with_requested_reviewers(keywords["with_requested_reviewers"])

    return builder.build()


if __name__ == '__main__':
    from unittest import main as run_tests
    run_tests()
