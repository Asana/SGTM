from src.codeowners.pr_assignment import (
    TRIGGER_REVIEW,
    TRIGGER_SYNC,
    TRIGGER_TASKS_CREATED,
    choose_outstanding_subtask,
    decide_pull_request_assignee,
)
from src.codeowners.state import CodeownerState, SubtaskState
from src.github.models import ReviewState
from test.codeowners.helpers import (
    AUTO_APPROVER,
    DATABRICKS,
    at,
    pull_request,
    review,
    summary_for,
)
from test.impl.base_test_case_class import BaseClass

AUTO_APPROVER_MAIN = "lambda/auto_approver/main.py"


def state_with_subtasks(pr, assignees, human_chosen=(), sgtm_assigned=None):
    """Requested state with one subtask per owner set, assigned per `assignees`
    (owner display -> login). `sgtm_assigned` is the login SGTM last set as
    the PR's assignee."""
    state = CodeownerState(tasks_requested_at="2026-09-11T19:30:00Z")
    for i, evaluation in enumerate(summary_for(pr).evaluations):
        key = evaluation.owner_set.key()
        state.subtasks[key] = SubtaskState(
            task_id=f"sub-{i}",
            owner_key=key,
            assignee=assignees.get(evaluation.owner_set.display()),
        )
    state.remember_human_chosen(list(human_chosen))
    if sgtm_assigned:
        state.remember_sgtm_assigned(sgtm_assigned)
    return state


class TestDecidePullRequestAssignee(BaseClass):
    def decide(self, pr, state, trigger, review=None, human_chosen=()):
        summary = summary_for(
            pr, human_chosen=human_chosen or state.human_chosen_logins
        )
        return decide_pull_request_assignee(pr, summary, state, trigger, review)

    def test_rules_do_not_apply_without_label_or_codeowned_files(self):
        approval = review("outsider", ReviewState.APPROVED, at(10))
        pr = pull_request([AUTO_APPROVER], reviews=[approval], assignees=["eli"])
        unrequested = CodeownerState()
        self.assertIsNone(self.decide(pr, unrequested, TRIGGER_REVIEW, approval))

        plain = pull_request(["README.md"], reviews=[approval], assignees=["eli"])
        state = state_with_subtasks(plain, {})
        self.assertIsNone(self.decide(plain, state, TRIGGER_REVIEW, approval))

    def test_changes_requested_goes_back_to_the_author(self):
        cr = review("eli", ReviewState.CHANGES_REQUESTED, at(10))
        pr = pull_request([AUTO_APPROVER], reviews=[cr], assignees=["eli"])
        state = state_with_subtasks(pr, {"secdev": "eli"}, sgtm_assigned="eli")
        self.assertEqual(self.decide(pr, state, TRIGGER_REVIEW, cr), "author")

        with_author = pull_request([AUTO_APPROVER], reviews=[cr], assignees=["author"])
        self.assertIsNone(self.decide(with_author, state, TRIGGER_REVIEW, cr))

    def test_approval_with_everything_satisfied_goes_to_the_author(self):
        reviews = [
            review("outsider", ReviewState.APPROVED, at(10)),
            review("jordan", ReviewState.APPROVED, at(11)),
        ]
        pr = pull_request([AUTO_APPROVER], reviews=reviews, assignees=["jordan"])
        state = state_with_subtasks(pr, {"secdev": "jordan"}, sgtm_assigned="jordan")
        self.assertEqual(self.decide(pr, state, TRIGGER_REVIEW, reviews[1]), "author")

    def test_primary_approval_with_outstanding_set_goes_to_the_subtask_assignee(
        self,
    ):
        approval = review("outsider", ReviewState.APPROVED, at(10))
        pr = pull_request([AUTO_APPROVER], reviews=[approval], assignees=["author"])
        state = state_with_subtasks(pr, {"secdev": "eli"})
        self.assertEqual(self.decide(pr, state, TRIGGER_REVIEW, approval), "eli")

    def test_escalated_subtask_sends_the_pr_to_the_author(self):
        approval = review("outsider", ReviewState.APPROVED, at(10))
        pr = pull_request([AUTO_APPROVER], reviews=[approval], assignees=["outsider"])
        state = state_with_subtasks(pr, {})  # nobody available: assignee None
        self.assertEqual(self.decide(pr, state, TRIGGER_REVIEW, approval), "author")

    def test_codeowner_approval_before_primary_goes_to_an_author_chosen_reviewer(
        self,
    ):
        approval = review("jordan", ReviewState.APPROVED, at(10))
        pr = pull_request([AUTO_APPROVER], reviews=[approval], assignees=["jordan"])
        state = state_with_subtasks(
            pr,
            {"secdev": "jordan"},
            human_chosen=["outsider"],
            sgtm_assigned="jordan",
        )
        self.assertEqual(self.decide(pr, state, TRIGGER_REVIEW, approval), "outsider")

        nobody_chosen = state_with_subtasks(
            pr, {"secdev": "jordan"}, sgtm_assigned="jordan"
        )
        self.assertIsNone(self.decide(pr, nobody_chosen, TRIGGER_REVIEW, approval))

    def test_author_requested_codeowner_approval_counts_as_primary(self):
        approval = review("jordan", ReviewState.APPROVED, at(10))
        pr = pull_request(
            [AUTO_APPROVER, DATABRICKS], reviews=[approval], assignees=["jordan"]
        )
        state = state_with_subtasks(
            pr, {"secdev": "jordan", "data": "dora"}, human_chosen=["jordan"]
        )
        # secdev is satisfied; data is outstanding and gets the PR.
        self.assertEqual(self.decide(pr, state, TRIGGER_REVIEW, approval), "dora")

    def test_a_codeowner_assigned_by_hand_keeps_the_pr(self):
        approval = review("outsider", ReviewState.APPROVED, at(10))
        pr = pull_request([AUTO_APPROVER], reviews=[approval], assignees=["pete"])
        state = state_with_subtasks(pr, {"secdev": "eli"})
        self.assertIsNone(self.decide(pr, state, TRIGGER_REVIEW, approval))

    def test_a_codeowner_a_person_put_in_charge_after_sgtm_keeps_the_pr(self):
        approval = review("outsider", ReviewState.APPROVED, at(10))
        pr = pull_request([AUTO_APPROVER], reviews=[approval], assignees=["eli"])
        # SGTM last handed the PR to the author; a person then assigned eli.
        state = state_with_subtasks(pr, {"secdev": "pete"}, sgtm_assigned="author")
        self.assertIsNone(self.decide(pr, state, TRIGGER_REVIEW, approval))
        self.assertIsNone(self.decide(pr, state, TRIGGER_SYNC))

    def test_current_outstanding_assignee_is_left_alone(self):
        approval = review("outsider", ReviewState.APPROVED, at(10))
        pr = pull_request([AUTO_APPROVER], reviews=[approval], assignees=["eli"])
        state = state_with_subtasks(pr, {"secdev": "eli"}, sgtm_assigned="eli")
        self.assertIsNone(self.decide(pr, state, TRIGGER_REVIEW, approval))

    def test_label_moves_the_pr_only_once_the_primary_review_is_in(self):
        pr = pull_request([AUTO_APPROVER], assignees=["author"])
        state = state_with_subtasks(pr, {"secdev": "eli"})
        self.assertIsNone(self.decide(pr, state, TRIGGER_TASKS_CREATED))

        approved = pull_request(
            [AUTO_APPROVER],
            reviews=[review("outsider", ReviewState.APPROVED, at(10))],
            assignees=["author"],
        )
        self.assertEqual(self.decide(approved, state, TRIGGER_TASKS_CREATED), "eli")

    def test_sync_follows_a_subtask_reassignment_sgtm_made(self):
        approval = review("outsider", ReviewState.APPROVED, at(10))
        pr = pull_request([AUTO_APPROVER], reviews=[approval], assignees=["eli"])
        # eli was replaced by pete on the subtask (out of office / idle).
        state = state_with_subtasks(pr, {"secdev": "pete"}, sgtm_assigned="eli")
        self.assertEqual(self.decide(pr, state, TRIGGER_SYNC), "pete")

        by_hand = state_with_subtasks(pr, {"secdev": "pete"})
        self.assertIsNone(self.decide(pr, by_hand, TRIGGER_SYNC))

    def test_sync_returns_the_pr_to_the_author_once_all_approved(self):
        reviews = [
            review("outsider", ReviewState.APPROVED, at(10)),
            review("jordan", ReviewState.APPROVED, at(11)),
        ]
        pr = pull_request([AUTO_APPROVER], reviews=reviews, assignees=["eli"])
        state = state_with_subtasks(pr, {"secdev": "eli"}, sgtm_assigned="eli")
        self.assertEqual(self.decide(pr, state, TRIGGER_SYNC), "author")
        pushes_do_not_move = pull_request(
            [AUTO_APPROVER], reviews=reviews, assignees=["outsider"]
        )
        self.assertIsNone(self.decide(pushes_do_not_move, state, TRIGGER_SYNC))

    def test_post_merge_approval_goes_to_the_author(self):
        approval = review("outsider", ReviewState.APPROVED, at(10))
        pr = pull_request(
            [AUTO_APPROVER], reviews=[approval], assignees=["eli"], merged=True
        )
        state = state_with_subtasks(pr, {"secdev": "eli"}, sgtm_assigned="eli")
        self.assertEqual(self.decide(pr, state, TRIGGER_REVIEW, approval), "author")

    def test_comment_only_review_changes_nothing(self):
        comment = review("outsider", ReviewState.COMMENTED, at(10))
        pr = pull_request([AUTO_APPROVER], reviews=[comment], assignees=["author"])
        state = state_with_subtasks(pr, {"secdev": "eli"})
        self.assertIsNone(self.decide(pr, state, TRIGGER_REVIEW, comment))


class TestChooseOutstandingSubtask(BaseClass):
    def test_prefers_author_chosen_then_fewest_files_then_earliest(self):
        pr = pull_request([AUTO_APPROVER, AUTO_APPROVER_MAIN, DATABRICKS])
        summary = summary_for(pr)

        fewest = state_with_subtasks(pr, {"secdev": "eli", "data": "dora"})
        chosen = choose_outstanding_subtask(summary, fewest)
        self.assertIsNotNone(chosen)
        self.assertEqual(chosen.assignee, "dora")  # data owns 1 file, secdev 2

        author_chosen = state_with_subtasks(
            pr, {"secdev": "eli", "data": "dora"}, human_chosen=["eli"]
        )
        chosen = choose_outstanding_subtask(summary, author_chosen)
        self.assertIsNotNone(chosen)
        self.assertEqual(chosen.assignee, "eli")

    def test_escalated_subtasks_rank_after_assigned_ones(self):
        pr = pull_request([AUTO_APPROVER, AUTO_APPROVER_MAIN, DATABRICKS])
        # data owns fewer files, but nobody was available to take it.
        state = state_with_subtasks(pr, {"secdev": "eli"})
        chosen = choose_outstanding_subtask(summary_for(pr), state)
        self.assertIsNotNone(chosen)
        self.assertEqual(chosen.assignee, "eli")

    def test_ties_break_on_creation_time_not_on_state_order(self):
        pr = pull_request([AUTO_APPROVER, DATABRICKS])
        summary = summary_for(pr)
        data_key, secdev_key = [e.owner_set.key() for e in summary.evaluations]
        state = CodeownerState(tasks_requested_at="2026-09-11T19:30:00Z")
        state.subtasks[data_key] = SubtaskState(
            task_id="sub-d",
            owner_key=data_key,
            assignee="dora",
            created_at="2026-09-11T19:35:00Z",
        )
        state.subtasks[secdev_key] = SubtaskState(
            task_id="sub-s",
            owner_key=secdev_key,
            assignee="eli",
            created_at="2026-09-11T19:30:00Z",
        )
        chosen = choose_outstanding_subtask(summary, state)
        self.assertIsNotNone(chosen)
        self.assertEqual(chosen.assignee, "eli")

    def test_only_outstanding_subtasks_count(self):
        pr = pull_request(
            [AUTO_APPROVER, DATABRICKS],
            reviews=[review("dora", ReviewState.APPROVED, at(10))],
        )
        state = state_with_subtasks(pr, {"secdev": "eli", "data": "dora"})
        chosen = choose_outstanding_subtask(summary_for(pr), state)
        self.assertIsNotNone(chosen)
        self.assertEqual(chosen.assignee, "eli")

        all_done = pull_request(["README.md"])
        self.assertIsNone(
            choose_outstanding_subtask(summary_for(all_done), CodeownerState())
        )


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
