from test.impl.base_test_case_class import BaseClass
from test.impl.builders import builder, build

from src.github.models import PullRequest


class TestPullRequest(BaseClass):
    def test_requested_reviewers_github_users_or_teams(self):
        user = build(builder.user().login("user1"))
        pull_request = build(
            builder.pull_request()
            .requested_reviewers([user])
            .requested_reviewer_team("some_team", ["user1", "user2"])
        )
        reviewers = pull_request.requested_reviewers()
        reviewer_logins = [reviewer.login for reviewer in reviewers]
        self.assertEqual(["user1", "user2"], reviewer_logins)


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
