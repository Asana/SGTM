from src.asana import helpers as asana_helpers
from src.github.models.commit import Commit
from test.impl.builders import builder, build

from test.impl.base_test_case_class import BaseClass


class TestBuildStatusFromPullRequest(BaseClass):
    def test_success(self):
        pull_request = build(
            builder.pull_request().commit(
                builder.commit().status(Commit.BUILD_SUCCESSFUL)
            )
        )
        build_status = asana_helpers._build_status_from_pull_request(pull_request)
        self.assertEqual("Success", build_status)

    def test_failure(self):
        pull_request = build(
            builder.pull_request().commit(
                builder.commit().status(Commit.BUILD_FAILED)
            )
        )
        build_status = asana_helpers._build_status_from_pull_request(pull_request)
        self.assertEqual("Failure", build_status)


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
