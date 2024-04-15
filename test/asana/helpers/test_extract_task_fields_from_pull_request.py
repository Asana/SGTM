from typing import List
import src.asana.helpers
import src.asana.client
from unittest.mock import patch
from src.github.models import ReviewState
from test.impl.mock_dynamodb_test_case import MockDynamoDbTestCase
from test.impl.builders import builder, build
from dataclasses import dataclass
from src.github.models import Commit
from src.github.logic import ApprovedBeforeMergeStatus
from src.asana import logic as asana_logic
from test.test_utils import magic_mock_with_return_type_value

followup_bot = builder.user("follow_up").build()


@dataclass
class EnumOptionSettingsForTests:
    name: str
    gid: str
    enabled: bool

    def __getitem__(self, item):
        return getattr(self, item)


@dataclass
class CustomFieldSettingForTests:
    name: str
    gid: str
    enum_options: List[EnumOptionSettingsForTests]
    resource_subtype: str = "enum"

    def __getitem__(self, item):
        return getattr(self, item)


def get_custom_fields(fields_to_disable: List[str]):
    return [
        {
            "custom_field": CustomFieldSettingForTests(
                name="PR Status",
                gid="pr_status",
                enum_options=[
                    EnumOptionSettingsForTests(
                        name="Open", gid="open", enabled="Open" not in fields_to_disable
                    ),
                    EnumOptionSettingsForTests(
                        name="Merged",
                        gid="merged",
                        enabled="Merged" not in fields_to_disable,
                    ),
                    EnumOptionSettingsForTests(
                        name="Closed",
                        gid="closed",
                        enabled="Closed" not in fields_to_disable,
                    ),
                ],
            )
        },
        {
            "custom_field": CustomFieldSettingForTests(
                name="Build",
                gid="build",
                enum_options=[
                    EnumOptionSettingsForTests(
                        name="Success",
                        gid="success",
                        enabled="Success" not in fields_to_disable,
                    ),
                    EnumOptionSettingsForTests(
                        name="Failure",
                        gid="failure",
                        enabled="Failure" not in fields_to_disable,
                    ),
                ],
            )
        },
    ]


class BaseClass(MockDynamoDbTestCase):
    @classmethod
    def setUpClass(cls):
        MockDynamoDbTestCase.setUpClass()

    def setUp(self) -> None:
        super(BaseClass, self).setUp()
        patch_get_asana_domain_user_id_from_github_handle = patch(
            "src.dynamodb.client.get_asana_domain_user_id_from_github_handle",
            magic_mock_with_return_type_value(
                {"github_test_user_login": "TEST_USER_ASANA_DOMAIN_USER_ID"}
            ),
        )
        patch_get_asana_domain_user_id_from_github_handle.start()
        self.addCleanup(patch_get_asana_domain_user_id_from_github_handle.stop)


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
            "This is a one-way sync from GitHub to Asana. Do not edit this task or"
            " comment on it!",
            "</em>",
            "\uD83D\uDD17",
            '<A href="https://foo.bar/baz">https://foo.bar/baz</A>',
            "✍",
            "TEST_USER_ASANA_DOMAIN_USER_ID",
            "<strong>",
            "Description:",
            "</strong>",
            "BODY",
            "</body>",
        ]
        self.assertContainsStrings(actual, expected_strings)

    def test_html_body_assigns_to_self(self):
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
            "This is a one-way sync from GitHub to Asana. Do not edit this task or"
            " comment on it!",
            "</em>",
            "\uD83D\uDD17",
            '<A href="https://foo.bar/baz">https://foo.bar/baz</A>',
            "✍",
            "TEST_USER_ASANA_DOMAIN_USER_ID",
            "Assigned to self",
            "<strong>",
            "Description:",
            "</strong>",
            "BODY",
            "</body>",
        ]
        self.assertContainsStrings(actual, expected_strings)

    def test_html_body_assigns_to_first(self):
        pull_request = build(
            builder.pull_request()
            .author(builder.user("github_test_user_login"))
            .url("https://foo.bar/baz")
            .body("BODY")
            .assignees(
                [
                    builder.user("github_assignee_login_billy"),
                    builder.user("github_assignee_login_annie"),
                ]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        actual = task_fields["html_notes"]
        expected_strings = [
            "<body>",
            "<em>",
            "This is a one-way sync from GitHub to Asana. Do not edit this task or"
            " comment on it!",
            "</em>",
            "\uD83D\uDD17",
            '<A href="https://foo.bar/baz">https://foo.bar/baz</A>',
            "✍",
            "TEST_USER_ASANA_DOMAIN_USER_ID",
            "first assignee alphabetically",
            "<strong>",
            "Description:",
            "</strong>",
            "BODY",
            "</body>",
        ]
        self.assertContainsStrings(actual, expected_strings)

    def test_html_body_status_not_closed(self):
        pull_request = build(
            builder.pull_request()
            .author(builder.user("github_test_user_login"))
            .url("https://foo.bar/baz")
            .body("BODY")
            .closed(False)
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        actual = task_fields["html_notes"]
        expected_strings = [
            "<body>",
            "incomplete",
            "the pull request is open.",
            "BODY",
            "</body>",
        ]
        self.assertContainsStrings(actual, expected_strings)

    def test_html_body_status_closed_not_merged(self):
        pull_request = build(
            builder.pull_request()
            .author(builder.user("github_test_user_login"))
            .url("https://foo.bar/baz")
            .body("BODY")
            .closed(True)
            .merged(False)
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        actual = task_fields["html_notes"]
        expected_strings = [
            "<body>",
            "closed",
            "the pull request was closed without merging code.",
            "BODY",
            "</body>",
        ]
        self.assertContainsStrings(actual, expected_strings)

    @patch("src.github.logic.pull_request_approved_before_merging")
    def test_html_body_status_closed_approved_before(self, approved_before_merging):
        approved_before_merging.return_value = ApprovedBeforeMergeStatus.APPROVED
        pull_request = build(
            builder.pull_request()
            .author(builder.user("github_test_user_login"))
            .url("https://foo.bar/baz")
            .body("BODY")
            .closed(True)
            .merged(True)
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        actual = task_fields["html_notes"]
        expected_strings = [
            "<body>",
            "complete",
            "the pull request was approved before merging.",
            "BODY",
            "</body>",
        ]
        self.assertContainsStrings(actual, expected_strings)

    @patch("src.github.logic.pull_request_approved_before_merging")
    def test_html_body_status_followup_review(self, approved_before_merging):
        approved_before_merging.return_value = ApprovedBeforeMergeStatus.NEEDS_FOLLOWUP
        pull_request = build(
            builder.pull_request()
            .author(builder.user("github_test_user_login"))
            .url("https://foo.bar/baz")
            .body("BODY")
            .closed(True)
            .merged(True)
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        actual = task_fields["html_notes"]
        expected_strings = [
            "<body>",
            "incomplete",
            "approved before merging by a Github user that requires follow-up",
            "BODY",
            "</body>",
        ]
        self.assertContainsStrings(actual, expected_strings)

    @patch("src.github.logic.pull_request_approved_before_merging")
    @patch("src.github.logic.pull_request_approved_after_merging")
    def test_html_body_status_closed_needs_followup_approved_after(
        self, approved_after_merging, approved_before_merging
    ):
        approved_before_merging.return_value = ApprovedBeforeMergeStatus.NEEDS_FOLLOWUP
        approved_after_merging.return_value = True
        pull_request = build(
            builder.pull_request()
            .author(builder.user("github_test_user_login"))
            .url("https://foo.bar/baz")
            .body("BODY")
            .closed(True)
            .merged(True)
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        actual = task_fields["html_notes"]
        expected_strings = [
            "<body>",
            "complete",
            "the pull request was approved after merging.",
            "BODY",
            "</body>",
        ]
        self.assertContainsStrings(actual, expected_strings)

    @patch("src.github.logic.pull_request_approved_before_merging")
    @patch("src.github.logic.pull_request_approved_after_merging")
    def test_html_body_status_closed_approved_after(
        self, approved_after_merging, approved_before_merging
    ):
        approved_before_merging.return_value = ApprovedBeforeMergeStatus.NO
        approved_after_merging.return_value = True
        pull_request = build(
            builder.pull_request()
            .author(builder.user("github_test_user_login"))
            .url("https://foo.bar/baz")
            .body("BODY")
            .closed(True)
            .merged(True)
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        actual = task_fields["html_notes"]
        expected_strings = [
            "<body>",
            "complete",
            "the pull request was approved after merging.",
            "BODY",
            "</body>",
        ]
        self.assertContainsStrings(actual, expected_strings)

    @patch("src.github.logic.pull_request_approved_before_merging")
    @patch("src.github.logic.pull_request_approved_after_merging")
    def test_html_body_status_merged_not_approved(
        self, approved_after_merging, approved_before_merging
    ):
        approved_before_merging.return_value = ApprovedBeforeMergeStatus.NO
        approved_after_merging.return_value = False
        pull_request = build(
            builder.pull_request()
            .author(builder.user("github_test_user_login"))
            .url("https://foo.bar/baz")
            .body("BODY")
            .closed(True)
            .merged(True)
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        actual = task_fields["html_notes"]
        expected_strings = [
            "<body>",
            "incomplete",
            "the pull request hasn't yet been approved by a reviewer after merging.",
            "BODY",
            "</body>",
        ]
        self.assertContainsStrings(actual, expected_strings)


@patch(
    "src.dynamodb.client.get_asana_domain_user_id_from_github_handle",
    magic_mock_with_return_type_value(
        {
            "github_assignee_login_annie": "ANNIE_ASANA_DOMAIN_USER_ID",
            "github_assignee_login_billy": "BILLY_ASANA_DOMAIN_USER_ID",
            "github_test_user_login": "TEST_USER_ASANA_DOMAIN_USER_ID",
        }
    ),
)
class TestExtractsAssigneeFromPullRequest(BaseClass):
    @classmethod
    def setUpClass(cls):
        BaseClass.setUpClass()

    @patch("src.asana.logic.SGTM_FEATURE__ALLOW_PERSISTENT_TASK_ASSIGNEE", False)
    def test_assignee(self):
        pull_request = build(
            builder.pull_request()
            .author(builder.user("github_test_user_login"))
            .assignee(builder.user("github_assignee_login_annie"))
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual("ANNIE_ASANA_DOMAIN_USER_ID", task_fields["assignee"])

    @patch("src.asana.logic.SGTM_FEATURE__ALLOW_PERSISTENT_TASK_ASSIGNEE", True)
    def test_assignee_persistent_owner(self):
        pull_request = build(
            builder.pull_request()
            .author(builder.user("github_test_user_login"))
            .assignee(builder.user("github_assignee_login_annie"))
            .label(builder.label().name(asana_logic.TaskAssigneeLabel.PERSISTENT.value))
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual("TEST_USER_ASANA_DOMAIN_USER_ID", task_fields["assignee"])

    @patch("src.asana.logic.SGTM_FEATURE__ALLOW_PERSISTENT_TASK_ASSIGNEE", False)
    def test_assignee_returns_first_assignee_by_login_if_many(self):
        pull_request = build(
            builder.pull_request()
            .author(builder.user("github_test_user_login"))
            .assignees(
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

    @patch("src.asana.logic.SGTM_FEATURE__ALLOW_PERSISTENT_TASK_ASSIGNEE", True)
    def test_assignee_multipe_assignees_persistent_owner(self):
        pull_request = build(
            builder.pull_request()
            .author(builder.user("github_test_user_login"))
            .assignees(
                [
                    builder.user("github_assignee_login_billy"),
                    builder.user("github_assignee_login_annie"),
                ]
            )
            .label(builder.label().name(asana_logic.TaskAssigneeLabel.PERSISTENT.value))
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual("TEST_USER_ASANA_DOMAIN_USER_ID", task_fields["assignee"])

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
            .merged_at("2020-01-13T14:59:59Z")
            .reviews(
                [
                    (
                        builder.review()
                        .submitted_at("2020-01-13T14:59:57Z")
                        .state(ReviewState.APPROVED)
                        .author(builder.user("human"))
                    ),
                    (
                        builder.review()
                        .submitted_at("2020-01-13T14:59:58Z")
                        .state(ReviewState.CHANGES_REQUESTED)
                        .author(builder.user("human"))
                    ),
                ]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(False, task_fields["completed"])

    @patch(
        "src.github.logic.SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS",
        {followup_bot.login()},
    )
    def test_completed_is_false_if_pr_is_closed_and_was_approved_by_followup_user(self):
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
                        .state(ReviewState.APPROVED)
                        .author(followup_bot)
                    )
                ]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(False, task_fields["completed"])

    @patch(
        "src.github.logic.SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS",
        {followup_bot.login()},
    )
    def test_completed_is_true_if_pr_is_closed_and_was_approved_by_human_and_followup_user(
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
                        .state(ReviewState.APPROVED)
                        .author(builder.user("human"))
                    ),
                    (
                        builder.review()
                        .submitted_at("2020-01-13T14:59:58Z")
                        .state(ReviewState.APPROVED)
                        .author(followup_bot)
                    ),
                ]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(True, task_fields["completed"])

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
                    .author(builder.user("human"))
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
                        .author(builder.user("human"))
                    ),
                    (
                        builder.review()
                        .submitted_at("2020-01-13T14:59:58Z")
                        .state(ReviewState.APPROVED)
                        .author(builder.user("human"))
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
                    .author(builder.user("human"))
                ]
            )
            .comments(
                [
                    builder.comment()
                    .published_at("2020-02-02T12:12:12Z")
                    .body("LGTM!")
                    .author(builder.user("human"))
                ]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(True, task_fields["completed"])

    def test_completed_is_false_if_pr_was_merged_and_changes_requested_and_commented_lgtm_on_the_pr_after_merge_by_author(
        self,
    ):
        author = builder.user().build()
        pull_request = build(
            builder.pull_request()
            .author(author)
            .closed(True)
            .merged(True)
            .merged_at("2020-01-13T14:59:59Z")
            .reviews(
                [
                    builder.review()
                    .submitted_at("2020-01-13T14:59:57Z")
                    .state(ReviewState.CHANGES_REQUESTED)
                    .author(builder.user("human"))
                ]
            )
            .comments(
                [
                    builder.comment()
                    .author(author)
                    .published_at("2020-02-02T12:12:12Z")
                    .body("LGTM!")
                ]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(False, task_fields["completed"])

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
                    .author(builder.user("human"))
                    .body("LGTM!")
                ]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(True, task_fields["completed"])


class TestTaskFollowersFromPullRequest(BaseClass):
    def test_author_is_a_follower(self):
        pull_request = build(
            builder.pull_request().author(builder.user("github_test_user_login"))
        )
        followers = src.asana.helpers.task_followers_from_pull_request(pull_request)
        self.assertIn("TEST_USER_ASANA_DOMAIN_USER_ID", followers)

    def test_assignee_is_a_follower(self):
        pull_request = build(
            builder.pull_request().assignee(
                builder.user("github_test_user_login", "TEST_USER_ASANA_DOMAIN_USER_ID")
            )
        )
        followers = src.asana.helpers.task_followers_from_pull_request(pull_request)
        self.assertIn("TEST_USER_ASANA_DOMAIN_USER_ID", followers)

    def test_requested_reviewer_is_a_follower(self):
        pull_request = build(
            builder.pull_request()
            .comments(
                [
                    builder.comment()
                    .published_at("2020-01-13T14:59:58Z")
                    .body("LGTM!"),
                ]
            )
            .requested_reviewers([builder.user("github_test_user_login")])
        )
        followers = src.asana.helpers.task_followers_from_pull_request(pull_request)
        self.assertIn("TEST_USER_ASANA_DOMAIN_USER_ID", followers)

    def test_individual_that_is_at_mentioned_in_pr_body_is_a_follower(self):
        pull_request = build(builder.pull_request().body("@github_test_user_login"))
        followers = src.asana.helpers.task_followers_from_pull_request(pull_request)
        self.assertIn("TEST_USER_ASANA_DOMAIN_USER_ID", followers)

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
        followers = src.asana.helpers.task_followers_from_pull_request(pull_request)
        self.assertEqual(0, len(followers))


class TestTaskFollowersFromReview(BaseClass):
    def test_reviewer_is_a_follower(self):
        review = (
            builder.review()
            .submitted_at("2020-02-13T14:59:57Z")
            .state(ReviewState.CHANGES_REQUESTED)
            .body("LGTM!")
            .author(builder.user("github_test_user_login"))
            .build()
        )
        followers = src.asana.helpers.task_followers_from_review(review)
        self.assertIn("TEST_USER_ASANA_DOMAIN_USER_ID", followers)

    def test_individual_that_is_at_mentioned_in_review_body_is_a_follower(self):
        review = builder.review().body("@github_test_user_login").build()
        followers = src.asana.helpers.task_followers_from_review(review)
        self.assertIn("TEST_USER_ASANA_DOMAIN_USER_ID", followers)

    def test_non_asana_user_is_not_a_follower(self):
        unknown_github_user = build(
            builder.user("github_unknown_user_login", "GITHUB_UNKNOWN_USER_NAME")
        )
        review = (
            builder.review()
            .body("@github_unknown_user_login")
            .author(unknown_github_user)
            .build()
        )
        followers = src.asana.helpers.task_followers_from_review(review)
        self.assertEqual(0, len(followers))


class TestTaskFollowersFromComment(BaseClass):
    def test_commentor_is_a_follower(self):
        comment = (
            builder.comment()
            .published_at("2020-01-13T14:59:58Z")
            .body("LGTM!")
            .author(builder.user("github_test_user_login"))
            .build()
        )
        followers = src.asana.helpers.task_followers_from_comment(comment)
        self.assertIn("TEST_USER_ASANA_DOMAIN_USER_ID", followers)

    def test_individual_that_is_at_mentioned_in_comment_is_a_follower(self):
        comment = builder.comment().body("@github_test_user_login").build()
        followers = src.asana.helpers.task_followers_from_comment(comment)
        self.assertIn("TEST_USER_ASANA_DOMAIN_USER_ID", followers)

    def test_non_asana_user_is_not_a_follower(self):
        unknown_github_user = build(
            builder.user("github_unknown_user_login", "GITHUB_UNKNOWN_USER_NAME")
        )
        comment = (
            builder.comment()
            .body("@github_unknown_user_login")
            .author(unknown_github_user)
            .build()
        )
        followers = src.asana.helpers.task_followers_from_comment(comment)
        self.assertEqual(0, len(followers))


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
                        .author(builder.user("human"))
                    ),
                    (
                        builder.review()
                        .submitted_at("2020-01-13T14:59:57Z")
                        .state(ReviewState.APPROVED)
                        .author(builder.user("human"))
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
                        .author(builder.user("human"))
                    ),
                    (
                        builder.review()
                        .submitted_at("2020-01-13T14:59:57Z")
                        .state(ReviewState.CHANGES_REQUESTED)
                        .author(builder.user("human"))
                    ),
                ]
            )
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )
        self.assertEqual(True, task_fields["completed"])


@patch("src.dynamodb.client.get_asana_id_from_github_node_id", return_value="0")
class TestExtractsCustomFieldsFromPullRequest(BaseClass):
    @patch(
        "src.asana.client.get_project_custom_fields", return_value=get_custom_fields([])
    )
    def test_pr_status_field_set_if_valid_option_and_enabled(
        self, get_asana_id_from_github_node_id, get_project_custom_fields
    ):
        pull_request = build(builder.pull_request().closed(False).isDraft(False))
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )

        self.assertIn("pr_status", task_fields["custom_fields"])
        self.assertIn("open", task_fields["custom_fields"]["pr_status"])
        self.assertNotIn("draft", task_fields["custom_fields"]["pr_status"])
        self.assertNotIn("merged", task_fields["custom_fields"]["pr_status"])
        self.assertNotIn("closed", task_fields["custom_fields"]["pr_status"])

    @patch(
        "src.asana.client.get_project_custom_fields",
        return_value=get_custom_fields(["Closed"]),
    )
    def test_pr_status_field_not_set_if_option_is_not_enabled(
        self, get_asana_id_from_github_node_id, get_project_custom_fields
    ):
        pull_request = build(
            builder.pull_request().closed(True).merged(False).isDraft(True)
        )
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )

        self.assertNotIn("pr_status", task_fields["custom_fields"])

    @patch(
        "src.asana.client.get_project_custom_fields", return_value=get_custom_fields([])
    )
    # In our mocked project custom field settings, "Draft" is not an option for the purpose of this test
    def test_pr_status_field_not_set_if_not_valid_option(
        self, get_asana_id_from_github_node_id, get_project_custom_fields
    ):
        pull_request = build(builder.pull_request().closed(False).isDraft(True))
        task_fields = src.asana.helpers.extract_task_fields_from_pull_request(
            pull_request
        )

        self.assertNotIn("pr_status", task_fields["custom_fields"])


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
