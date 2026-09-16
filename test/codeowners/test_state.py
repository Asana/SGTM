from src.codeowners.state import CodeownerState, SubtaskState, parse_iso
from test.impl.mock_dynamodb_test_case import MockDynamoDbTestCase


class TestCodeownerState(MockDynamoDbTestCase):
    def test_round_trip(self):
        state = CodeownerState(tasks_requested_at="2026-09-11T19:30:00Z")
        state.remember_human_chosen(["thelma", "thelma"])
        state.remember_sgtm_requested("vignir")
        state.subtasks["Asana/platform"] = SubtaskState(
            task_id="task-1",
            owner_key="Asana/platform",
            assignee="vignir",
            assigned_at="2026-09-11T19:30:00Z",
            assignment_reason="picked at random",
            status="Needed",
            files=["modules/cell/data.tf"],
            manual=False,
            notes_hash="abc",
        )
        state.save("PR_node")

        loaded = CodeownerState.load("PR_node")
        self.assertTrue(loaded.tasks_requested)
        self.assertEqual(loaded.human_chosen_logins, ["thelma"])
        self.assertEqual(loaded.sgtm_requested_logins, ["vignir"])
        self.assertEqual(
            loaded.subtasks["Asana/platform"], state.subtasks["Asana/platform"]
        )
        self.assertEqual(
            parse_iso(loaded.tasks_requested_at).isoformat(),
            "2026-09-11T19:30:00+00:00",
        )

    def test_missing_state_is_empty(self):
        state = CodeownerState.load("PR_unknown")
        self.assertFalse(state.tasks_requested)
        self.assertEqual(state.subtasks, {})

    def test_unknown_document_keys_are_ignored(self):
        loaded = CodeownerState.from_document(
            {"tasks_requested_at": None, "future_field": 1, "subtasks": {}}
        )
        self.assertFalse(loaded.tasks_requested)

    def test_unknown_subtask_keys_are_ignored(self):
        loaded = CodeownerState.from_document(
            {
                "tasks_requested_at": "2026-09-11T19:30:00Z",
                "subtasks": {
                    "Asana/platform": {
                        "task_id": "task-1",
                        "owner_key": "Asana/platform",
                        "future_subtask_field": True,
                    }
                },
            }
        )
        sub = loaded.subtasks["Asana/platform"]
        self.assertEqual(sub.task_id, "task-1")
        self.assertIsNone(sub.created_at)


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
