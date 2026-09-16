from unittest.mock import MagicMock, call, patch

from github import GithubException, UnknownObjectException

import src.github.client as github_client
from test.impl.base_test_case_class import BaseClass


class TestEnsureLabel(BaseClass):
    @patch.object(github_client, "_get_repo")
    def test_creates_label_when_missing(self, get_repo_mock):
        repo = MagicMock()
        repo.get_label.side_effect = UnknownObjectException(404, {}, {})
        get_repo_mock.return_value = repo

        github_client.ensure_label(
            "Asana", "codez", "assign-tasks-to-codeowners", "1d76db", "desc"
        )

        repo.get_label.assert_called_once_with("assign-tasks-to-codeowners")
        repo.create_label.assert_called_once_with(
            name="assign-tasks-to-codeowners", color="1d76db", description="desc"
        )

    @patch.object(github_client, "_get_repo")
    def test_description_is_cut_to_githubs_limit(self, get_repo_mock):
        repo = MagicMock()
        repo.get_label.side_effect = UnknownObjectException(404, {}, {})
        get_repo_mock.return_value = repo

        github_client.ensure_label("Asana", "codez", "lbl", "1d76db", "x" * 130)

        self.assertEqual(len(repo.create_label.call_args.kwargs["description"]), 100)

    @patch.object(github_client, "_get_repo")
    def test_concurrent_creation_is_not_an_error(self, get_repo_mock):
        repo = MagicMock()
        repo.get_label.side_effect = UnknownObjectException(404, {}, {})
        repo.create_label.side_effect = GithubException(
            422, {"errors": [{"code": "already_exists"}]}, {}
        )
        get_repo_mock.return_value = repo

        github_client.ensure_label("Asana", "codez", "lbl", "1d76db", "desc")

        repo.create_label.side_effect = GithubException(500, {}, {})
        with self.assertRaises(GithubException):
            github_client.ensure_label("Asana", "codez", "lbl", "1d76db", "desc")

    @patch.object(github_client, "_get_repo")
    def test_leaves_existing_label_alone(self, get_repo_mock):
        repo = MagicMock()
        get_repo_mock.return_value = repo

        github_client.ensure_label("Asana", "codez", "existing", "1d76db", "desc")

        repo.create_label.assert_not_called()


class TestRequestReviewers(BaseClass):
    @patch.object(github_client, "_get_pull_request")
    def test_requests_reviewers(self, get_pull_request_mock):
        pr = MagicMock()
        get_pull_request_mock.return_value = pr

        requested = github_client.request_reviewers(
            "Asana", "codez", 42, ["alice", "bob"]
        )

        self.assertEqual(requested, ["alice", "bob"])
        pr.create_review_request.assert_has_calls(
            [call(reviewers=["alice"]), call(reviewers=["bob"])]
        )

    @patch.object(github_client, "_get_pull_request")
    def test_one_rejected_login_does_not_block_the_others(self, get_pull_request_mock):
        pr = MagicMock()
        pr.create_review_request.side_effect = [
            GithubException(422, {"message": "not a collaborator"}, {}),
            None,
        ]
        get_pull_request_mock.return_value = pr

        requested = github_client.request_reviewers(
            "Asana", "codez", 42, ["gone", "bob"]
        )

        self.assertEqual(requested, ["bob"])
        self.assertEqual(pr.create_review_request.call_count, 2)

    @patch.object(github_client, "_get_pull_request")
    def test_no_reviewers_makes_no_request(self, get_pull_request_mock):
        github_client.request_reviewers("Asana", "codez", 42, [])
        get_pull_request_mock.assert_not_called()


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
