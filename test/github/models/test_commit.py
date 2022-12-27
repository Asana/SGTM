from test.impl.base_test_case_class import BaseClass

from src.github.models import Commit


class TestCommit(BaseClass):
    def test_status_check_rollup_success(self):
        raw_commit = {
            "commit": {"statusCheckRollup": {"state": Commit.BUILD_SUCCESSFUL}}
        }
        commit = Commit(raw_commit)
        self.assertEqual(commit.status(), Commit.BUILD_SUCCESSFUL)

    def test_status_check_rollup_none(self):
        raw_commit = {"commit": {"statusCheckRollup": None}}
        commit = Commit(raw_commit)
        self.assertEqual(commit.status(), None)


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
