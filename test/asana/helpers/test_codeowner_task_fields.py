from unittest.mock import patch

import src.asana.client
import src.asana.helpers
import src.aws.dynamodb_client as dynamodb_client
from src.codeowners.context import CodeownerTaskContext
from src.codeowners.state import CodeownerState, SubtaskState
from src.github.models import ReviewState
from test.codeowners.helpers import (
    AUTO_APPROVER,
    CELL_DATA,
    at,
    gid_for,
    pull_request,
    review,
    summary_for,
)
from test.impl.mock_dynamodb_test_case import MockDynamoDbTestCase

PROJECT_FIELDS = [
    {
        "custom_field": {
            "name": "Review Status",
            "gid": "cf-review",
            "resource_subtype": "enum",
            "enum_options": [
                {"name": name, "gid": f"rs-{i}", "enabled": True}
                for i, name in enumerate(
                    [
                        "Needs Review",
                        "Changes Requested",
                        "Approved",
                        "Not Ready",
                        "Needs Codeowner Approval",
                    ]
                )
            ],
        }
    },
    {
        "custom_field": {
            "name": "Codeowner Review (SGTM)",
            "gid": "cf-codeowner-review",
            "resource_subtype": "enum",
            "enum_options": [
                {"name": name, "gid": f"cr-{i}", "enabled": True}
                for i, name in enumerate(
                    [
                        "Not Required",
                        "Not Yet Requested",
                        "Pending",
                        "Partially Approved",
                        "Approved",
                        "Changes Requested",
                    ]
                )
            ],
        }
    },
    {
        "custom_field": {
            "name": "Codeowners Pending (SGTM)",
            "gid": "cf-pending",
            "resource_subtype": "text",
        }
    },
]


@patch("src.asana.helpers.config.SGTM_FEATURE__CODEOWNER_TASKS_ENABLED", True)
@patch("src.aws.s3_client.get_asana_domain_user_id_from_github_handle", gid_for)
@patch.object(
    src.asana.client, "get_project_custom_fields", return_value=PROJECT_FIELDS
)
class TestCodeownerTaskFields(MockDynamoDbTestCase):
    def fields(self, pr, context):
        dynamodb_client.insert_github_node_to_asana_id_mapping(
            pr.repository_id(), "project-1"
        )
        return src.asana.helpers.extract_task_fields_from_pull_request(pr, context)

    def context(self, pr, tasks_requested=True, human_chosen=(), subtasks=None):
        summary = summary_for(pr, tasks_requested, human_chosen)
        state = CodeownerState(
            tasks_requested_at="2026-09-11T19:30:00Z" if tasks_requested else None,
            subtasks=subtasks or {},
        )
        return CodeownerTaskContext(summary, state, "assign-tasks-to-codeowners")

    def test_before_the_label(self, _fields):
        pr = pull_request([CELL_DATA, AUTO_APPROVER])
        task_fields = self.fields(pr, self.context(pr, tasks_requested=False))
        custom = task_fields["custom_fields"]
        self.assertEqual(custom["cf-review"], "rs-0")  # Needs Review
        self.assertEqual(custom["cf-codeowner-review"], "cr-1")  # Not Yet Requested
        self.assertIn("secdev", custom["cf-pending"])
        self.assertContainsStrings(
            task_fields["html_notes"],
            [
                "Codeowner reviews: not yet requested",
                "<code>assign-tasks-to-codeowners</code>",
                "Codeowner tracking on this task comes from SGTM's opt-in",
            ],
        )

    def test_primary_approved_codeowner_outstanding(self, _fields):
        pr = pull_request(
            [AUTO_APPROVER], reviews=[review("outsider", ReviewState.APPROVED, at(10))]
        )
        key = summary_for(pr).evaluations[0].owner_set.key()
        subtasks = {
            key: SubtaskState(task_id="sub-1", owner_key=key, assignee="jordan")
        }
        task_fields = self.fields(pr, self.context(pr, subtasks=subtasks))
        custom = task_fields["custom_fields"]
        self.assertEqual(custom["cf-review"], "rs-4")  # Needs Codeowner Approval
        self.assertEqual(custom["cf-codeowner-review"], "cr-2")  # Pending
        self.assertEqual(custom["cf-pending"], "secdev")
        self.assertContainsStrings(
            task_fields["html_notes"],
            [
                "Codeowner reviews: 0 of 1 approved",
                "⬜",
                "gid-jordan",
                'data-asana-gid="sub-1"',
            ],
        )

    def test_everything_approved(self, _fields):
        pr = pull_request(
            [AUTO_APPROVER],
            reviews=[
                review("outsider", ReviewState.APPROVED, at(10)),
                review("jordan", ReviewState.APPROVED, at(11)),
            ],
        )
        task_fields = self.fields(pr, self.context(pr))
        custom = task_fields["custom_fields"]
        self.assertEqual(custom["cf-review"], "rs-2")  # Approved
        self.assertEqual(custom["cf-codeowner-review"], "cr-4")  # Approved
        self.assertEqual(custom["cf-pending"], "")
        self.assertIn("Codeowner reviews: 1 of 1 approved", task_fields["html_notes"])

    def test_no_codeowned_files_leaves_legacy_behaviour(self, _fields):
        pr = pull_request(
            ["README.md"], reviews=[review("outsider", ReviewState.APPROVED, at(10))]
        )
        task_fields = self.fields(pr, self.context(pr, tasks_requested=False))
        custom = task_fields["custom_fields"]
        self.assertEqual(custom["cf-review"], "rs-2")  # Approved as today
        self.assertEqual(custom["cf-codeowner-review"], "cr-0")  # Not Required
        self.assertEqual(custom["cf-pending"], "")
        self.assertNotIn("🛡️", task_fields["html_notes"])
        self.assertNotIn("Codeowner tracking", task_fields["html_notes"])

    def test_without_context_nothing_changes(self, _fields):
        pr = pull_request(
            [AUTO_APPROVER], reviews=[review("outsider", ReviewState.APPROVED, at(10))]
        )
        task_fields = self.fields(pr, None)
        custom = task_fields["custom_fields"]
        self.assertEqual(custom["cf-review"], "rs-2")
        self.assertNotIn("cf-codeowner-review", custom)
        self.assertNotIn("cf-pending", custom)


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
