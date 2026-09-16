from datetime import date
from unittest.mock import patch

import src.codeowners.texts as texts
from src.codeowners.requirements import OwnerSet
from src.codeowners.state import CodeownerState, SubtaskState
from src.github.models import ReviewState
from test.codeowners.helpers import (
    AUTO_APPROVER,
    CELL_DATA,
    CELL_LOCALS,
    at,
    evaluations_for,
    gid_for,
    pull_request,
    review,
    summary_for,
)
from test.impl.base_test_case_class import BaseClass


@patch("src.aws.s3_client.get_asana_domain_user_id_from_github_handle", gid_for)
class TestSubtaskTexts(BaseClass):
    def test_name_with_and_without_owner_set(self):
        pr = pull_request([CELL_DATA])
        owner_set = OwnerSet.of(["@Asana/platform-workday-sync", "@Asana/secdev"])
        self.assertEqual(
            texts.subtask_name(pr, owner_set, several_sets=False),
            "Codeowner review: #436513 - Plumb permissionsCluster into cell Helm globals",
        )
        self.assertEqual(
            texts.subtask_name(pr, owner_set, several_sets=True),
            "Codeowner review (platform + secdev): #436513 - Plumb"
            " permissionsCluster into cell Helm globals",
        )

    def test_description_needed(self):
        pr = pull_request([CELL_DATA, CELL_LOCALS, "README.md"])
        evaluation = evaluations_for(pr)[0]
        html = texts.subtask_description(
            pr, evaluation, "parent-1", "vignir", texts_reason()
        )
        self.assertContainsStrings(
            html,
            [
                "<body>",
                "one-way sync",
                'href="https://github.com/Asana/codez/pull/436513"',
                'data-asana-gid="parent-1"',
                "#436513 - Plumb permissionsCluster into cell Helm globals",
                "https://github.com/orgs/Asana/teams/platform",
                "(any member can approve)",
                'data-asana-gid="gid-author"',
                "<strong>Needed</strong>",
                "No codeowner has approved the latest commit (0fb846e3)",
                'data-asana-gid="gid-vignir"',
                "Codeowned files changed in this PR (2 of 3)",
                "changes?owned-by%5B%5D=vignir#diff-",
                "modules/cell/data.tf</a> — needs approval",
                "Only the files you own, as vignir sees them",
                "https://github.com/Asana/codez/pull/436513/files",
                "To complete this task",
                "ℹ️ Created by SGTM's opt-in codeowner tasks feature.",
                "How it works",
                "</body>",
            ],
        )
        self.assertNotIn("also owned by", html)

    def test_description_marks_folded_files(self):
        pr = pull_request([AUTO_APPROVER, CELL_DATA])
        evaluation = evaluations_for(pr)[0]
        html = texts.subtask_description(pr, evaluation, "parent-1", "jordan", "x")
        self.assertIn("also owned by", html)
        self.assertIn("Files marked", html)

    def test_description_approved_and_escalated(self):
        pr = pull_request(
            [AUTO_APPROVER], reviews=[review("jordan", ReviewState.APPROVED, at(10))]
        )
        evaluation = evaluations_for(pr)[0]
        html = texts.subtask_description(
            pr, evaluation, "parent-1", None, texts.REASON_NOBODY if False else ""
        )
        self.assertContainsStrings(
            html,
            ["<strong>Approved</strong>", "Approved by", "gid-jordan", "on abc12345"],
        )
        self.assertNotIn("👤", html)

    @patch("src.config.SGTM_FEATURE__CODEOWNER_TASKS_OPT_IN_COMMAND", "z sgtm opt-in")
    @patch("src.config.SGTM_FEATURE__CODEOWNER_TASKS_ORG_DOCS_URL", "https://docs/x")
    def test_footer_includes_command_and_org_docs(self):
        footer = texts.footer_html("Created by SGTM.")
        self.assertContainsStrings(
            footer,
            ["<code>z sgtm opt-in</code>", "How it works", 'href="https://docs/x"'],
        )


@patch("src.aws.s3_client.get_asana_domain_user_id_from_github_handle", gid_for)
class TestSubtaskComments(BaseClass):
    def test_comments(self):
        approval = review("thelma", ReviewState.APPROVED, at(10))
        owner_set = OwnerSet.of(["@Asana/platform"])
        self.assertContainsStrings(
            texts.comment_reassigned_out_of_office("eli", "jordan", date(2026, 9, 22)),
            ["gid-eli", "gid-jordan", "out of office in Asana until Sep 22"],
        )
        self.assertIn(
            "after 1 business day without a review",
            texts.comment_reassigned_idle("eli", 1),
        )
        self.assertIn(
            "after 2 business days without a review",
            texts.comment_reassigned_idle("eli", 2),
        )
        self.assertIn(
            "everyone is the PR author or out of office",
            texts.comment_escalated("author"),
        )
        self.assertContainsStrings(
            texts.comment_approved(approval, owner_set),
            [
                "gid-thelma",
                "abc12345",
                "Marking this task complete",
                "reopens if a later push",
            ],
        )
        self.assertIn(
            "Approved after merge", texts.comment_approved_after_merge(approval)
        )
        self.assertContainsStrings(
            texts.comment_approval_dismissed("jordan", "e434ab0448"),
            ["Reopening", "gid-jordan", "(e434ab04)"],
        )
        cr = review("eli", ReviewState.CHANGES_REQUESTED, at(11))
        self.assertContainsStrings(
            texts.comment_changes_requested(cr, "jordan"),
            ["gid-eli", "requested changes", "back with the author", "gid-jordan"],
        )
        self.assertContainsStrings(
            texts.comment_no_longer_required([CELL_DATA]),
            ["Completing", "<li>modules/cell/data.tf</li>", "reopens if"],
        )
        self.assertContainsStrings(
            texts.comment_required_again([CELL_DATA]), ["Reopening", CELL_DATA]
        )
        self.assertContainsStrings(
            texts.comment_merged_with_bypass("author"),
            ["gid-author", "ruleset bypass", "Nothing is required here"],
        )
        self.assertEqual(
            texts.comment_closed_unmerged(),
            "<body>PR closed without merging. Closing.</body>",
        )


@patch("src.aws.s3_client.get_asana_domain_user_id_from_github_handle", gid_for)
class TestParentTexts(BaseClass):
    def test_not_requested_block(self):
        pr = pull_request([CELL_DATA, AUTO_APPROVER])
        summary = summary_for(pr, tasks_requested=False)
        block = texts.parent_not_requested_block(summary.codeowned_files, "the-label")
        self.assertContainsStrings(
            block,
            [
                "not yet requested",
                "2 files are owned by",
                "<code>the-label</code>",
                "https://github.com/orgs/Asana/teams/secdev",
            ],
        )

    def test_checklist_block_and_all_approved_comment(self):
        pr = pull_request(
            [CELL_DATA, DATABRICKS_PATH()],
            reviews=[review("thelma", ReviewState.APPROVED, at(10))],
        )
        summary = summary_for(pr)
        state = CodeownerState(
            subtasks={
                e.owner_set.key(): SubtaskState(
                    task_id=f"task-{i}", owner_key=e.owner_set.key(), assignee="dora"
                )
                for i, e in enumerate(summary.evaluations)
            }
        )
        block = texts.parent_checklist_block(
            summary,
            {k: s.assignee for k, s in state.subtasks.items()},
            {k: s.task_id for k, s in state.subtasks.items()},
        )
        self.assertContainsStrings(
            block,
            [
                "Codeowner reviews: 1 of 2 approved",
                "✅",
                "approved by",
                "gid-thelma",
                "⬜",
                "needed · assigned to",
                "gid-dora",
                'data-asana-gid="task-',
                ">subtask</A>",
            ],
        )
        comment = texts.parent_all_approved_comment(summary)
        self.assertContainsStrings(
            comment, ["All codeowner approvals are in place", "gid-thelma"]
        )


class TestGithubTexts(BaseClass):
    def test_heads_up_comment_plain_and_stacked(self):
        pr = pull_request([CELL_DATA, CELL_LOCALS])
        summary = summary_for(pr, tasks_requested=False)
        plain = texts.heads_up_comment(
            summary.codeowned_files,
            1,
            "assign-tasks-to-codeowners",
            "next-master",
            "next-master",
            False,
        )
        self.assertContainsStrings(
            plain,
            [
                texts.HEADS_UP_MARKER,
                "**Codeowner review required.** This PR changes 2 files that have",
                "| `modules/cell/data.tf` | [cicd](https://github.com/orgs/Asana/teams/cicd)",
                "add the `assign-tasks-to-codeowners` label",
                "(1 here)",
                "Prefer a specific codeowner?",
                "latest** push",
                "Docs: [SGTM codeowner tasks](",
            ],
        )
        self.assertNotIn("not trunk", plain)
        self.assertNotIn("@Asana/", plain)

        stacked = texts.heads_up_comment(
            summary.codeowned_files, 1, "lbl", "feature/parent", "next-master", False
        )
        self.assertIn("**This PR targets `feature/parent`, not trunk.**", stacked)
        native = texts.heads_up_comment(
            summary.codeowned_files, 1, "lbl", "feature/parent", "next-master", True
        )
        self.assertNotIn("not trunk", native)

    def test_label_added_comment_and_created_block(self):
        pr = pull_request([CELL_DATA])
        summary = summary_for(pr)
        key = summary.evaluations[0].owner_set.key()
        owner_sets = {key: summary.evaluations[0].owner_set}
        comment = texts.label_added_comment(
            "assign-tasks-to-codeowners",
            summary.codeowned_files,
            {key: "vignir"},
            {key: "https://app.asana.com/0/0/1"},
            owner_sets,
            {key: "picked at random"},
        )
        self.assertContainsStrings(
            comment,
            [
                texts.CREATED_MARKER,
                "**`assign-tasks-to-codeowners` label added.**",
                "creates Asana tasks for the codeowner reviews",
                "**✅ Task created.**",
                "[vignir](https://github.com/vignir), picked at random · [Asana](https://app.asana.com/0/0/1)",
                "Prefer someone else?",
                "Want a heads-up like this",
            ],
        )
        block = texts.created_block_markdown({key: None}, {}, owner_sets, {})
        self.assertContainsStrings(
            block,
            ["---", "**✅ Codeowner review task created.**", "no codeowner available"],
        )


def DATABRICKS_PATH():
    from test.codeowners.helpers import DATABRICKS

    return DATABRICKS


def texts_reason():
    from src.codeowners.assignment import REASON_RANDOM

    return REASON_RANDOM


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
