from test.impl.base_test_case_class import BaseClass

from src.github.models import Commit


class TestCommit(BaseClass):
    def test_status_success(self):
        raw_commit = {"commit": {"status": {"state": Commit.BUILD_SUCCESSFUL}}}
        commit = Commit(raw_commit)
        self.assertEqual(commit.status(), Commit.BUILD_SUCCESSFUL)

    def test_status_none(self):
        raw_commit = {"commit": {"status": None}}
        commit = Commit(raw_commit)
        self.assertEqual(commit.status(), None)

    def test_status_falls_back_to_status_rollup(self):
        raw_commit = {
            "commit": {
                "status": None,
                "statusCheckRollup": {"state": Commit.BUILD_PENDING},
            }
        }
        commit = Commit(raw_commit)
        self.assertEqual(commit.status(), Commit.BUILD_PENDING)


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
