from unittest.mock import patch

import src.github.logic as github_logic
from test.impl.base_test_case_class import BaseClass
from test.impl.builders import builder, build


class TestParticipantsWithCodeownerTasks(BaseClass):
    def pull_request(self):
        human = build(builder.user().login("human-pick"))
        return build(
            builder.pull_request()
            .author(builder.user("author"))
            .requested_reviewer(human)
            .requested_reviewer_team("platform", ["carol"])
            .requested_reviewer_team("secdev", ["alice", "bob"], as_code_owner=True)
        )

    @patch.object(github_logic, "SGTM_FEATURE__CODEOWNER_TASKS_ENABLED", True)
    def test_codeowner_auto_requests_do_not_follow(self):
        participants = sorted(
            github_logic.pull_request_participants(self.pull_request())
        )
        self.assertEqual(participants, ["author", "carol", "human-pick"])

    @patch.object(github_logic, "SGTM_FEATURE__CODEOWNER_TASKS_ENABLED", False)
    def test_legacy_behaviour_when_disabled(self):
        participants = sorted(
            github_logic.pull_request_participants(self.pull_request())
        )
        self.assertEqual(
            participants, ["alice", "author", "bob", "carol", "human-pick"]
        )


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
