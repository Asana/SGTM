from datetime import date
from uuid import uuid4
from unittest.mock import patch

import src.asana.client as asana_client
import src.codeowners.controller as codeowner_controller
import src.github.client as github_client
import src.github.graphql.client as github_graphql_client
from src.codeowners import texts
from src.codeowners.state import CodeownerState
from src.codeowners.status import ParentCodeownerStatus
from src.github.models import ReviewState
from test.codeowners.helpers import (
    AUTO_APPROVER,
    CELL_DATA,
    CELL_LOCALS,
    CODEOWNERS_TEXT,
    TEAM_MEMBERS,
    at,
    gid_for,
    login_for,
    pull_request,
    review,
)
from test.impl.mock_dynamodb_test_case import MockDynamoDbTestCase

LABEL = "assign-tasks-to-codeowners"


def codeowners_file(org_name, owner, repository, ref, path):
    return CODEOWNERS_TEXT if path == ".github/CODEOWNERS" else None


def team_members(org, slug):
    return sorted(TEAM_MEMBERS.get(f"{org}/{slug}", set()))


@patch("src.config.SGTM_FEATURE__CODEOWNER_TASKS_ENABLED", True)
@patch("src.config.SGTM_FEATURE__CODEOWNER_TASKS_LABEL", LABEL)
@patch("src.aws.s3_client.get_asana_domain_user_id_from_github_handle", gid_for)
@patch("src.aws.s3_client.get_github_handle_from_asana_domain_user_id", login_for)
@patch("src.aws.s3_client.is_opted_in_to_codeowner_tasks", return_value=False)
@patch.object(github_graphql_client, "load_all_changed_files")
@patch.object(github_graphql_client, "get_team_members", side_effect=team_members)
@patch.object(
    github_graphql_client, "get_repository_file_content", side_effect=codeowners_file
)
@patch.object(github_client, "set_pull_request_assignee")
@patch.object(github_client, "request_reviewers")
@patch.object(github_client, "ensure_label")
@patch.object(github_client, "edit_comment")
@patch.object(github_client, "add_pr_comment", return_value=1001)
@patch.object(asana_client, "get_project_custom_fields", return_value=[])
@patch.object(asana_client, "get_task", return_value={"assignee": None})
@patch.object(asana_client, "reopen_task")
@patch.object(asana_client, "complete_task")
@patch.object(asana_client, "add_followers")
@patch.object(asana_client, "add_comment")
@patch.object(asana_client, "update_task")
@patch.object(asana_client, "create_subtask", return_value="sub-1")
class TestCodeownerControllerSync(MockDynamoDbTestCase):
    def setUp(self):
        codeowner_controller.reset_caches()
        self.pr_id = f"PR_{uuid4().hex}"

    def pr(self, files, **kwargs):
        """A snapshot of this test's pull request."""
        return pull_request(files, node_id=self.pr_id, **kwargs)

    def sync(self, pr, review=None):
        return codeowner_controller.sync(pr, "parent-1", review=review, now=at(20))

    def test_disabled_feature_returns_none(self, create_subtask, *mocks):
        with patch("src.config.SGTM_FEATURE__CODEOWNER_TASKS_ENABLED", False):
            self.assertIsNone(self.sync(self.pr([CELL_DATA], labels=[LABEL])))
        create_subtask.assert_not_called()

    def test_repository_without_codeowners_file(
        self,
        create_subtask,
        update_task,
        add_comment,
        add_followers,
        complete_task,
        reopen_task,
        get_task,
        get_project_custom_fields,
        add_pr_comment,
        edit_comment,
        ensure_label,
        request_reviewers,
        set_assignee,
        get_file_content,
        *mocks,
    ):
        get_file_content.side_effect = lambda *args: None
        context = self.sync(self.pr([CELL_DATA], labels=[LABEL]))
        assert context is not None
        self.assertFalse(context.summary.has_codeowned_files())
        self.assertEqual(
            context.summary.parent_status(), ParentCodeownerStatus.NOT_REQUIRED
        )
        self.assertFalse(context.manages_pull_request_assignee())
        ensure_label.assert_not_called()
        add_pr_comment.assert_not_called()
        create_subtask.assert_not_called()
        # CODEOWNERS was looked for in every location GitHub checks.
        self.assertEqual(get_file_content.call_count, 3)

    def test_heads_up_comment_for_opted_in_author(
        self,
        create_subtask,
        update_task,
        add_comment,
        add_followers,
        complete_task,
        reopen_task,
        get_task,
        get_project_custom_fields,
        add_pr_comment,
        edit_comment,
        ensure_label,
        request_reviewers,
        set_assignee,
        get_file_content,
        get_team_members,
        load_files,
        opted_in,
        *mocks,
    ):
        opted_in.return_value = True
        pr = self.pr([CELL_DATA, "README.md"])
        context = self.sync(pr)
        assert context is not None

        ensure_label.assert_called_once_with(
            "Asana", "codez", LABEL, texts.LABEL_COLOR, texts.label_description()
        )
        add_pr_comment.assert_called_once()
        body = add_pr_comment.call_args.args[3]
        self.assertIn(texts.HEADS_UP_MARKER, body)
        self.assertIn("This PR changes 1 file that has", body)
        self.assertEqual(
            context.summary.parent_status(), ParentCodeownerStatus.NOT_YET_REQUESTED
        )
        create_subtask.assert_not_called()

        saved = CodeownerState.load(pr.id())
        self.assertEqual(saved.heads_up_comment_id, 1001)
        self.assertFalse(saved.tasks_requested)

        # Same files again: nothing to post or edit.
        self.sync(pr)
        add_pr_comment.assert_called_once()
        edit_comment.assert_not_called()

        # More codeowned files: the comment is brought up to date.
        self.sync(self.pr([CELL_DATA, CELL_LOCALS]))
        edit_comment.assert_called_once()
        self.assertEqual(edit_comment.call_args.args[3], 1001)
        self.assertIn("This PR changes 2 files", edit_comment.call_args.args[4])

    def test_authors_who_did_not_opt_in_get_no_heads_up(
        self, create_subtask, update_task, add_comment, *mocks
    ):
        add_pr_comment = mocks[5]
        self.sync(self.pr([CELL_DATA]))
        add_pr_comment.assert_not_called()

    def test_label_creates_subtasks_requests_reviews_and_confirms(
        self,
        create_subtask,
        update_task,
        add_comment,
        add_followers,
        complete_task,
        reopen_task,
        get_task,
        get_project_custom_fields,
        add_pr_comment,
        edit_comment,
        ensure_label,
        request_reviewers,
        set_assignee,
        *mocks,
    ):
        pr = self.pr([AUTO_APPROVER], labels=[LABEL])
        context = self.sync(pr)
        assert context is not None

        create_subtask.assert_called_once()
        saved = CodeownerState.load(pr.id())
        self.assertTrue(saved.tasks_requested)
        sub = list(saved.subtasks.values())[0]
        self.assertEqual(sub.task_id, "sub-1")
        self.assertIn(sub.assignee, TEAM_MEMBERS["Asana/secdev"])
        request_reviewers.assert_called_once_with(
            "Asana", "codez", 436513, [sub.assignee]
        )
        self.assertEqual(saved.sgtm_requested_logins, [sub.assignee])

        add_pr_comment.assert_called_once()
        body = add_pr_comment.call_args.args[3]
        self.assertIn(texts.CREATED_MARKER, body)
        self.assertIn(f"[{sub.assignee}](https://github.com/{sub.assignee})", body)
        self.assertIn("https://app.asana.com/0/0/sub-1", body)
        self.assertEqual(saved.created_comment_id, 1001)

        self.assertTrue(context.manages_pull_request_assignee())
        self.assertEqual(context.summary.parent_status(), ParentCodeownerStatus.PENDING)
        # No primary review yet: the PR stays with the author.
        set_assignee.assert_not_called()

        # A second sync is quiet.
        self.sync(self.pr([AUTO_APPROVER], labels=[LABEL]))
        add_pr_comment.assert_called_once()
        create_subtask.assert_called_once()
        request_reviewers.assert_called_once()

    def test_label_after_heads_up_edits_that_comment(
        self,
        create_subtask,
        update_task,
        add_comment,
        add_followers,
        complete_task,
        reopen_task,
        get_task,
        get_project_custom_fields,
        add_pr_comment,
        edit_comment,
        ensure_label,
        request_reviewers,
        set_assignee,
        get_file_content,
        get_team_members,
        load_files,
        opted_in,
        *mocks,
    ):
        opted_in.return_value = True
        self.sync(self.pr([AUTO_APPROVER]))
        add_pr_comment.assert_called_once()

        pr = self.pr([AUTO_APPROVER], labels=[LABEL])
        self.sync(pr)
        add_pr_comment.assert_called_once()  # no second comment
        edit_comment.assert_called_once()
        body = edit_comment.call_args.args[4]
        self.assertIn(texts.HEADS_UP_MARKER, body)
        self.assertIn("**✅ Codeowner review task created.**", body)
        saved = CodeownerState.load(pr.id())
        self.assertEqual(saved.created_comment_id, saved.heads_up_comment_id)

    def test_draft_with_label_waits_until_ready_for_review(
        self, create_subtask, *mocks
    ):
        pr = self.pr([AUTO_APPROVER], labels=[LABEL], draft=True)
        context = self.sync(pr)
        assert context is not None
        create_subtask.assert_not_called()
        self.assertFalse(CodeownerState.load(pr.id()).tasks_requested)
        self.assertFalse(context.manages_pull_request_assignee())

        self.sync(self.pr([AUTO_APPROVER], labels=[LABEL]))
        create_subtask.assert_called_once()

    def test_label_on_a_closed_pull_request_does_nothing(self, create_subtask, *mocks):
        add_pr_comment = mocks[7]
        pr = self.pr([AUTO_APPROVER], labels=[LABEL], closed=True)
        self.sync(pr)
        create_subtask.assert_not_called()
        add_pr_comment.assert_not_called()
        self.assertFalse(CodeownerState.load(pr.id()).tasks_requested)

    def test_reviewers_and_assignees_a_person_chose_are_remembered(
        self, create_subtask, *mocks
    ):
        pr = self.pr(
            [AUTO_APPROVER],
            labels=[LABEL],
            requested=["outsider"],
            assignees=["thelma"],
            codeowner_teams=["Asana/secdev"],
        )
        context = self.sync(pr)
        assert context is not None
        saved = CodeownerState.load(pr.id())
        self.assertEqual(sorted(saved.human_chosen_logins), ["outsider", "thelma"])
        self.assertEqual(context.summary.human_chosen_logins, {"outsider", "thelma"})

        # People SGTM itself requested are not mistaken for the author's choice.
        assignee = list(saved.subtasks.values())[0].assignee
        again = self.pr(
            [AUTO_APPROVER], labels=[LABEL], requested=["outsider", assignee]
        )
        self.sync(again)
        self.assertNotIn(assignee, CodeownerState.load(pr.id()).human_chosen_logins)

    def test_all_approved_comment_is_posted_once(
        self, create_subtask, update_task, add_comment, *mocks
    ):
        approved = self.pr(
            [AUTO_APPROVER],
            labels=[LABEL],
            reviews=[review("jordan", ReviewState.APPROVED, at(10))],
        )
        context = self.sync(approved)
        assert context is not None
        self.assertEqual(
            context.summary.parent_status(), ParentCodeownerStatus.APPROVED
        )
        parent_comments = [
            c.args[1] for c in add_comment.call_args_list if c.args[0] == "parent-1"
        ]
        self.assertEqual(len(parent_comments), 1)
        self.assertIn("All codeowner approvals are in place", parent_comments[0])
        self.assertTrue(CodeownerState.load(approved.id()).all_approved_commented)

        self.sync(approved)
        parent_comments = [
            c for c in add_comment.call_args_list if c.args[0] == "parent-1"
        ]
        self.assertEqual(len(parent_comments), 1)

    def test_primary_approval_moves_the_pull_request_to_the_codeowner(
        self,
        create_subtask,
        update_task,
        add_comment,
        add_followers,
        complete_task,
        reopen_task,
        get_task,
        get_project_custom_fields,
        add_pr_comment,
        edit_comment,
        ensure_label,
        request_reviewers,
        set_assignee,
        *mocks,
    ):
        pr = self.pr([AUTO_APPROVER], labels=[LABEL])
        self.sync(pr)
        assignee = list(CodeownerState.load(pr.id()).subtasks.values())[0].assignee

        approval = review("outsider", ReviewState.APPROVED, at(10))
        reviewed = self.pr(
            [AUTO_APPROVER], labels=[LABEL], reviews=[approval], assignees=["author"]
        )
        context = self.sync(reviewed, review=approval)
        assert context is not None
        set_assignee.assert_called_once_with("Asana", "codez", 436513, assignee)
        self.assertEqual(reviewed.assignees(), [assignee])
        self.assertEqual(CodeownerState.load(pr.id()).sgtm_assigned_logins, [assignee])

        # The codeowner approves too: back to the author.
        codeowner_approval = review(assignee, ReviewState.APPROVED, at(11))
        done = self.pr(
            [AUTO_APPROVER],
            labels=[LABEL],
            reviews=[approval, codeowner_approval],
            assignees=[assignee],
        )
        self.sync(done, review=codeowner_approval)
        self.assertEqual(set_assignee.call_args.args[3], "author")
        self.assertEqual(done.assignees(), ["author"])

    @patch("src.codeowners.status.SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS", {"bot"})
    @patch("src.config.SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS", {"bot"})
    def test_followup_reviewers_do_not_move_the_pull_request(
        self,
        create_subtask,
        update_task,
        add_comment,
        add_followers,
        complete_task,
        reopen_task,
        get_task,
        get_project_custom_fields,
        add_pr_comment,
        edit_comment,
        ensure_label,
        request_reviewers,
        set_assignee,
        *mocks,
    ):
        approval = review("bot", ReviewState.APPROVED, at(10))
        pr = self.pr([AUTO_APPROVER], labels=[LABEL], reviews=[approval])
        self.sync(pr, review=approval)
        set_assignee.assert_not_called()

    def test_out_of_office_lookup_uses_the_configured_workspace(self, *mocks):
        lookup = codeowner_controller.OutOfOfficeLookup(date(2026, 9, 14))
        self.assertIsNone(lookup("jordan"))  # no workspace configured
        with patch(
            "src.config.SGTM_FEATURE__CODEOWNER_TASKS_ASANA_WORKSPACE_ID", "ws-1"
        ), patch.object(
            asana_client, "out_of_office_until", return_value=date(2026, 9, 22)
        ) as ooo:
            lookup = codeowner_controller.OutOfOfficeLookup(date(2026, 9, 14))
            self.assertEqual(lookup("jordan"), date(2026, 9, 22))
            self.assertEqual(lookup("jordan"), date(2026, 9, 22))  # memoised
            ooo.assert_called_once_with("gid-jordan", "ws-1", date(2026, 9, 14))
            self.assertIsNone(lookup("unmapped-user"))

    def test_lookup_failure_falls_back_to_plain_behaviour(
        self,
        create_subtask,
        update_task,
        add_comment,
        add_followers,
        complete_task,
        reopen_task,
        get_task,
        get_project_custom_fields,
        add_pr_comment,
        edit_comment,
        ensure_label,
        request_reviewers,
        set_assignee,
        get_file_content,
        *mocks,
    ):
        get_file_content.side_effect = ValueError("no Contents: Read permission")
        pr = self.pr([AUTO_APPROVER], labels=[LABEL])
        self.assertIsNone(self.sync(pr))
        create_subtask.assert_not_called()
        add_pr_comment.assert_not_called()
        self.assertFalse(CodeownerState.load(pr.id()).tasks_requested)

    def test_codeowners_is_read_from_the_stack_base_for_native_stacks(
        self,
        create_subtask,
        update_task,
        add_comment,
        add_followers,
        complete_task,
        reopen_task,
        get_task,
        get_project_custom_fields,
        add_pr_comment,
        edit_comment,
        ensure_label,
        request_reviewers,
        set_assignee,
        get_file_content,
        *mocks,
    ):
        from test.impl.builders import build, builder

        pr = build(
            builder.pull_request()
            .author(builder.user("author"))
            .files([AUTO_APPROVER])
            .base_ref_name("feature/parent")
            .stack_base_ref_name("next-master")
        )
        self.sync(pr)
        refs = {call.args[3] for call in get_file_content.call_args_list}
        self.assertEqual(refs, {"next-master"})

        codeowner_controller.reset_caches()
        get_file_content.reset_mock()
        plain = build(
            builder.pull_request()
            .author(builder.user("author"))
            .files([AUTO_APPROVER])
            .base_ref_name("feature/parent")
        )
        self.sync(plain)
        refs = {call.args[3] for call in get_file_content.call_args_list}
        self.assertEqual(refs, {"feature/parent"})


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
