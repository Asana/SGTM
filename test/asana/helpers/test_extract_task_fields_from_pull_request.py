from datetime import datetime, timedelta

import src.asana.helpers
from test.asana.helpers.base_class import BaseClass


class TestExtractsFieldsFromPullRequest(BaseClass):

    def test_none_causes_valueerror(self):
        try:
            src.asana.helpers.extract_task_fields_from_pull_request(None)
            self.fail("This code should have been unreachable")
        except ValueError:
            pass

    def test_name(self):
        pull_request = create_pull_request(number="PR_NUMBER", title="PR_TITLE")
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual("#PR_NUMBER - PR_TITLE", task_fields["name"])

    def test_assignee(self):
        assignee_nodes = [{"login": "GITHUB_ASSIGNEE_LOGIN"}]
        pull_request = create_pull_request(assignees={"nodes": assignee_nodes})
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual("ASSIGNEE_ASANA_DOMAIN_USER_ID", task_fields["assignee"])

    def test_assignee_returns_first_assignee_by_login_if_many(self):
        assignee_nodes = [{"login": "GITHUB_ASSIGNEE_LOGIN_BILLY"}, {"login": "GITHUB_ASSIGNEE_LOGIN_ANNIE"}]
        pull_request = create_pull_request(assignees={"nodes": assignee_nodes})
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual("ANNIE_ASANA_DOMAIN_USER_ID", task_fields["assignee"])

    def test_assignee_returns_author_when_assignees_are_empty(self):
        pull_request = create_pull_request()
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual("AUTHOR_ASANA_DOMAIN_USER_ID", task_fields["assignee"])

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

    def test_completed_is_true_if_pr_was_merged_with_changes_requested_and_commented_lgtm_in_a_review_after_merge(self):
        # this is an edge case supported by the code (presumably ported from previous version), but which is a bit
        # bizarre. A review was created before the pr was merged, but a comment on it had LGTM! in it after the merge.
        # This was considered sufficient proof of completion, even though the PR now has a review requesting changes.
        # The end state may make sense, but the sequence of human interactions leading to this state seems a bit
        # bizarre.
        pull_request = create_pull_request(
            closed=True, merged=True, merged_at="2020-01-13T14:59:59Z", with_reviews=[
                create_review(submitted_at="2020-01-13T14:59:57Z", state="CHANGES_REQUESTED", with_comments=[
                    create_comment(created_at="2020-02-02T12:12:12Z", body="LGTM!")
                ]),
            ])
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(pull_request)
        self.assertEqual(True, task_fields["completed"])


"""
        "followers": _task_followers_from_pull_request(pull_request),
"""


class TestExtractsFieldsFromPullRequestInconsistentData(BaseClass):
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


def create_comment(**keywords):
    from test.github.helpers import CommentBuilder
    builder = CommentBuilder()
    for k, v in keywords.items():
        builder.raw_comment[k] = v
    return builder.build()


def create_review(**keywords):
    from test.github.helpers import ReviewBuilder
    builder = ReviewBuilder()
    for k, v in keywords.items():
        if not k.startswith("with_"):
            builder.raw_review[k] = v
    if "with_comments" in keywords:
        builder = builder.with_comments(keywords["with_comments"])
    return builder.build()


def create_pull_request(**keywords):
    from test.github.helpers import PullRequestBuilder
    builder = PullRequestBuilder().with_author("GITHUB_AUTHOR_LOGIN", "GITHUB_AUTHOR_NAME")
    for k, v in keywords.items():
        if not k.startswith("with_"):
            builder.raw_pr[k] = v
    if "with_reviews" in keywords:
        builder = builder.with_reviews(keywords["with_reviews"])
    if "with_comments" in keywords:
        builder = builder.with_comments(keywords["with_comments"])
    return builder.build()


if __name__ == '__main__':
    from unittest import main as run_tests
    run_tests()
