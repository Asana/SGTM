import random
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, call, patch

import src.asana.client as asana_client
import src.codeowners.tasks as tasks
from src.codeowners.assignment import (
    REASON_ENGAGED,
    REASON_HUMAN_REQUESTED,
    REASON_RANDOM,
)
from src.codeowners.state import CodeownerState, SubtaskState
from src.codeowners.status import RequirementStatus
from src.github.models import ReviewState
from test.codeowners.helpers import (
    AUTO_APPROVER,
    CELL_DATA,
    CELL_LOCALS,
    DATABRICKS,
    at,
    gid_for,
    login_for,
    pull_request,
    resolve_pool,
    review,
    summary_for,
)
from test.impl.base_test_case_class import BaseClass

PROJECT_FIELDS = [
    {
        "custom_field": {
            "name": "Codeowner Approval (SGTM)",
            "gid": "cf-approval",
            "resource_subtype": "enum",
            "enum_options": [
                {"name": status.value, "gid": f"opt-{status.name}", "enabled": True}
                for status in RequirementStatus
            ],
        }
    },
    {
        "custom_field": {
            "name": "Codeowners (SGTM)",
            "gid": "cf-owners",
            "resource_subtype": "text",
        }
    },
]


def no_ooo(login):
    return None


@patch("src.config.SGTM_FEATURE__CODEOWNER_TASKS_PROJECT_ID", "project-1")
@patch("src.aws.s3_client.get_github_handle_from_asana_domain_user_id", login_for)
@patch("src.aws.s3_client.get_asana_domain_user_id_from_github_handle", gid_for)
@patch.object(asana_client, "get_project_custom_fields", return_value=PROJECT_FIELDS)
@patch.object(asana_client, "get_task")
@patch.object(asana_client, "reopen_task")
@patch.object(asana_client, "complete_task")
@patch.object(asana_client, "add_followers")
@patch.object(asana_client, "add_comment")
@patch.object(asana_client, "update_task")
@patch.object(asana_client, "add_task_to_project")
@patch.object(asana_client, "create_subtask", return_value="sub-1")
class TestSyncSubtasks(BaseClass):
    NOW = at(20, day=11)

    def sync(self, pr, state, ooo=no_ooo, now=None, rng_seed=1, tasks_requested=True):
        if tasks_requested and not state.tasks_requested:
            state.tasks_requested_at = "2026-09-11T19:30:00Z"
        inputs = tasks.SubtaskSyncInputs(
            pull_request=pr,
            parent_task_id="parent-1",
            summary=summary_for(pr, tasks_requested=tasks_requested),
            state=state,
            resolve_pool=resolve_pool,
            out_of_office_until=ooo,
            now=now or self.NOW,
            rng=random.Random(rng_seed),
        )
        return tasks.sync_subtasks(inputs)

    def test_nothing_happens_before_the_label(
        self, create_subtask, add_to_project, update_task, add_comment, *_
    ):
        state = CodeownerState()
        result = self.sync(pull_request([CELL_DATA]), state, tasks_requested=False)
        create_subtask.assert_not_called()
        self.assertEqual(result.newly_assigned_logins, [])
        self.assertEqual(state.subtasks, {})

    def test_creates_one_subtask_per_owner_set(
        self,
        create_subtask,
        add_to_project,
        update_task,
        add_comment,
        add_followers,
        complete_task,
        *_,
    ):
        pr = pull_request([CELL_DATA, CELL_LOCALS])
        state = CodeownerState()
        result = self.sync(pr, state)

        create_subtask.assert_called_once()
        parent, fields = create_subtask.call_args.args
        self.assertEqual(parent, "parent-1")
        self.assertTrue(fields["name"].startswith("Codeowner review: #436513"))
        assignee_login = login_for(fields["assignee"])
        self.assertIn(
            assignee_login,
            resolve_pool(
                list(state.subtasks.values())[0]
                and summary_for(pr).evaluations[0].owner_set
            ),
        )
        self.assertNotEqual(assignee_login, "author")
        add_to_project.assert_called_once_with("sub-1", "project-1")

        update = update_task.call_args.args[1]
        self.assertIn("html_notes", update)
        self.assertEqual(update["custom_fields"]["cf-approval"], "opt-NEEDED")
        self.assertEqual(update["custom_fields"]["cf-owners"], "cicd, platform, secdev")

        add_followers.assert_called_once()
        followers = add_followers.call_args.args[1]
        self.assertIn("gid-author", followers)
        add_comment.assert_not_called()
        complete_task.assert_not_called()

        sub = state.subtasks[summary_for(pr).evaluations[0].owner_set.key()]
        self.assertEqual(sub.task_id, "sub-1")
        self.assertEqual(sub.assignee, assignee_login)
        self.assertEqual(sub.assignment_reason, REASON_RANDOM)
        self.assertEqual(sub.status, "Needed")
        self.assertEqual(result.newly_assigned_logins, [assignee_login])
        self.assertIn(assignee_login, state.sgtm_requested_logins)

    def test_prefers_human_requested_then_engaged(
        self, create_subtask, add_to_project, update_task, add_comment, *_
    ):
        pr = pull_request(
            [AUTO_APPROVER], reviews=[review("eli", ReviewState.COMMENTED, at(9))]
        )
        state = CodeownerState()
        self.sync(pr, state)
        sub = list(state.subtasks.values())[0]
        self.assertEqual(sub.assignee, "eli")
        self.assertEqual(sub.assignment_reason, REASON_ENGAGED)

        state = CodeownerState(human_chosen_logins=["pete"])
        self.sync(pr, state)
        sub = list(state.subtasks.values())[0]
        self.assertEqual(sub.assignee, "pete")
        self.assertEqual(sub.assignment_reason, REASON_HUMAN_REQUESTED)
        self.assertTrue(sub.manual is False)

    def test_escalates_when_everyone_is_out(
        self, create_subtask, add_to_project, update_task, add_comment, *_
    ):
        pr = pull_request([AUTO_APPROVER])
        state = CodeownerState()
        result = self.sync(pr, state, ooo=lambda login: date.max)
        fields = create_subtask.call_args.args[1]
        self.assertEqual(fields["assignee"], "gid-author")
        add_comment.assert_called_once()
        self.assertIn("No available codeowner", add_comment.call_args.args[1])
        self.assertIsNone(list(state.subtasks.values())[0].assignee)
        self.assertEqual(result.newly_assigned_logins, [])

    def test_approval_completes_and_dismissal_reopens(
        self,
        create_subtask,
        add_to_project,
        update_task,
        add_comment,
        add_followers,
        complete_task,
        reopen_task,
        get_task,
        *_,
    ):
        get_task.return_value = {"assignee": {"gid": "gid-jordan"}}
        state = CodeownerState()
        self.sync(pull_request([AUTO_APPROVER]), state, rng_seed=3)
        sub = list(state.subtasks.values())[0]
        sub.assignee = "jordan"  # pin for the rest of the test

        approved = pull_request(
            [AUTO_APPROVER], reviews=[review("jordan", ReviewState.APPROVED, at(10))]
        )
        self.sync(approved, state)
        complete_task.assert_called_once_with("sub-1")
        self.assertIn("Approved by", add_comment.call_args.args[1])
        self.assertEqual(sub.status, "Approved")
        self.assertTrue(sub.completed)

        dismissed = pull_request(
            [AUTO_APPROVER], reviews=[review("jordan", ReviewState.DISMISSED, at(11))]
        )
        self.sync(dismissed, state)
        reopen_task.assert_called_once_with("sub-1")
        self.assertIn("Reopening: the approval from", add_comment.call_args.args[1])
        self.assertEqual(sub.status, "Approval Stale")
        self.assertFalse(sub.completed)

    def test_changes_requested_comment(
        self, create_subtask, add_to_project, update_task, add_comment, *_
    ):
        state = CodeownerState()
        self.sync(pull_request([AUTO_APPROVER]), state)
        cr = pull_request(
            [AUTO_APPROVER],
            reviews=[review("eli", ReviewState.CHANGES_REQUESTED, at(10))],
        )
        self.sync(cr, state)
        self.assertIn("requested changes", add_comment.call_args.args[1])
        self.assertEqual(list(state.subtasks.values())[0].status, "Changes Requested")

    def test_orphaned_requirement_is_retired_and_revived(
        self,
        create_subtask,
        add_to_project,
        update_task,
        add_comment,
        add_followers,
        complete_task,
        reopen_task,
        *_,
    ):
        state = CodeownerState()
        self.sync(pull_request([AUTO_APPROVER]), state)
        key = list(state.subtasks)[0]

        # The author drops the codeowned file from the diff.
        self.sync(pull_request(["README.md"]), state)
        complete_task.assert_called_once_with("sub-1")
        self.assertIn("no longer changes any file", add_comment.call_args.args[1])
        self.assertIn(AUTO_APPROVER, add_comment.call_args.args[1])
        self.assertEqual(state.subtasks[key].status, "No Longer Required")
        # Field set to No Longer Required
        self.assertEqual(
            update_task.call_args.args[1]["custom_fields"]["cf-approval"],
            "opt-NO_LONGER_REQUIRED",
        )

        # ...and brings it back.
        self.sync(pull_request([AUTO_APPROVER]), state)
        reopen_task.assert_called_once_with("sub-1")
        self.assertIn("Reopening: the PR again changes", add_comment.call_args.args[1])
        self.assertEqual(state.subtasks[key].status, "Needed")
        create_subtask.assert_called_once()  # no second subtask

    def test_out_of_office_assignee_is_replaced(
        self, create_subtask, add_to_project, update_task, add_comment, *_
    ):
        state = CodeownerState()
        self.sync(pull_request([AUTO_APPROVER]), state)
        sub = list(state.subtasks.values())[0]
        first = sub.assignee
        assert first is not None

        result = self.sync(
            pull_request([AUTO_APPROVER]),
            state,
            ooo=lambda login: date(2026, 9, 22) if login == first else None,
        )
        self.assertNotEqual(sub.assignee, first)
        self.assertIn(
            "out of office in Asana until Sep 22", add_comment.call_args.args[1]
        )
        self.assertEqual(result.newly_assigned_logins, [sub.assignee])

    def test_idle_assignee_is_replaced_after_a_business_day(
        self, create_subtask, add_to_project, update_task, add_comment, *_
    ):
        state = CodeownerState()
        self.sync(pull_request([AUTO_APPROVER]), state)
        sub = list(state.subtasks.values())[0]
        first = sub.assignee
        sub.assigned_at = "2026-09-11T15:00:00Z"  # a Friday

        # Saturday: not idle yet.
        self.sync(pull_request([AUTO_APPROVER]), state, now=at(9, day=12))
        self.assertEqual(sub.assignee, first)
        # Monday: one business day, re-pick.
        self.sync(pull_request([AUTO_APPROVER]), state, now=at(9, day=14))
        self.assertNotEqual(sub.assignee, first)
        self.assertIn(
            "after 1 business day without a review", add_comment.call_args.args[1]
        )

    def test_engaged_assignee_is_not_idle(
        self, create_subtask, add_to_project, update_task, add_comment, *_
    ):
        state = CodeownerState()
        self.sync(pull_request([AUTO_APPROVER]), state)
        sub = list(state.subtasks.values())[0]
        first = sub.assignee
        sub.assigned_at = "2026-09-11T15:00:00Z"
        engaged = pull_request(
            [AUTO_APPROVER],
            reviews=[review(first, ReviewState.COMMENTED, at(16, day=11))],
        )
        self.sync(engaged, state, now=at(9, day=15))
        self.assertEqual(sub.assignee, first)

    def test_author_requested_codeowner_takes_over(
        self, create_subtask, add_to_project, update_task, add_comment, *_
    ):
        state = CodeownerState()
        self.sync(pull_request([AUTO_APPROVER]), state, rng_seed=3)
        sub = list(state.subtasks.values())[0]
        other = "pete" if sub.assignee != "pete" else "eli"
        state.remember_human_chosen([other])
        self.sync(pull_request([AUTO_APPROVER]), state)
        self.assertEqual(sub.assignee, other)
        self.assertTrue(sub.manual)
        self.assertIn("who was requested as a reviewer", add_comment.call_args.args[1])

    def test_manual_reassignment_in_asana_is_adopted(
        self,
        create_subtask,
        add_to_project,
        update_task,
        add_comment,
        add_followers,
        complete_task,
        reopen_task,
        get_task,
        *_,
    ):
        state = CodeownerState()
        self.sync(pull_request([AUTO_APPROVER]), state, rng_seed=3)
        sub = list(state.subtasks.values())[0]
        other = "pete" if sub.assignee != "pete" else "eli"
        get_task.return_value = {"assignee": {"gid": gid_for(other)}}
        self.sync(pull_request([AUTO_APPROVER]), state)
        self.assertEqual(sub.assignee, other)
        self.assertTrue(sub.manual)
        self.assertIn(other, state.human_chosen_logins)

    def test_merged_with_bypass_stays_open_then_completes_on_late_approval(
        self,
        create_subtask,
        add_to_project,
        update_task,
        add_comment,
        add_followers,
        complete_task,
        *_,
    ):
        state = CodeownerState()
        self.sync(pull_request([AUTO_APPROVER]), state)
        self.sync(pull_request([AUTO_APPROVER], merged=True), state)
        sub = list(state.subtasks.values())[0]
        self.assertEqual(sub.status, "Merged with Bypass")
        complete_task.assert_not_called()
        self.assertIn("ruleset bypass", add_comment.call_args.args[1])

        late = pull_request(
            [AUTO_APPROVER],
            reviews=[review("jordan", ReviewState.APPROVED, at(12))],
            merged=True,
        )
        self.sync(late, state)
        complete_task.assert_called_once_with("sub-1")
        self.assertIn("Approved after merge", add_comment.call_args.args[1])

    def test_closed_unmerged_completes_with_comment(
        self,
        create_subtask,
        add_to_project,
        update_task,
        add_comment,
        add_followers,
        complete_task,
        *_,
    ):
        state = CodeownerState()
        self.sync(pull_request([AUTO_APPROVER]), state)
        self.sync(pull_request([AUTO_APPROVER], closed=True), state)
        complete_task.assert_called_once_with("sub-1")
        self.assertEqual(
            add_comment.call_args.args[1],
            "<body>PR closed without merging. Closing.</body>",
        )

    def test_unchanged_task_is_not_rewritten(
        self, create_subtask, add_to_project, update_task, add_comment, *_
    ):
        state = CodeownerState()
        pr = pull_request([AUTO_APPROVER])
        self.sync(pr, state)
        calls_after_create = update_task.call_count
        self.sync(pr, state)
        self.assertEqual(update_task.call_count, calls_after_create)


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
