from unittest.mock import patch, call

from src.github.graphql import client
from src.github.graphql.queries import GetPullRequestFiles, GetRepositoryFileContent
from test.impl.base_test_case_class import BaseClass
from test.impl.builders import builder, build


def _files_page(paths, has_next_page, end_cursor):
    return {
        "pullRequest": {
            "files": {
                "pageInfo": {"hasNextPage": has_next_page, "endCursor": end_cursor},
                "nodes": [{"path": path} for path in paths],
            }
        }
    }


@patch.object(client, "_execute_graphql_query")
class TestPullRequestFiles(BaseClass):
    ORG = "Asana"

    def test_single_page(self, mock_query):
        mock_query.return_value = _files_page(["a", "b"], False, "c1")
        paths, cursor = client.get_pull_request_files(self.ORG, "PR_1")
        self.assertEqual(paths, ["a", "b"])
        self.assertIsNone(cursor)
        mock_query.assert_called_once_with(
            self.ORG, GetPullRequestFiles, {"pullRequestId": "PR_1"}
        )

    def test_load_all_changed_files_pages_until_done(self, mock_query):
        pull_request = build(builder.pull_request().files(["a", "b"], True, "c1"))
        mock_query.side_effect = [
            _files_page(["c"], True, "c2"),
            _files_page(["d"], False, None),
        ]
        client.load_all_changed_files(self.ORG, pull_request)
        self.assertEqual(pull_request.changed_files(), ["a", "b", "c", "d"])
        self.assertFalse(pull_request.has_unloaded_changed_files())
        mock_query.assert_has_calls(
            [
                call(
                    self.ORG,
                    GetPullRequestFiles,
                    {"pullRequestId": pull_request.id(), "cursor": "c1"},
                ),
                call(
                    self.ORG,
                    GetPullRequestFiles,
                    {"pullRequestId": pull_request.id(), "cursor": "c2"},
                ),
            ]
        )

    def test_load_all_changed_files_is_a_noop_when_complete(self, mock_query):
        pull_request = build(builder.pull_request().files(["a"]))
        client.load_all_changed_files(self.ORG, pull_request)
        mock_query.assert_not_called()
        self.assertEqual(pull_request.changed_files(), ["a"])


@patch.object(client, "_execute_graphql_query")
class TestRepositoryFileContent(BaseClass):
    ORG = "Asana"

    def test_returns_text(self, mock_query):
        mock_query.return_value = {
            "repository": {
                "object": {
                    "__typename": "Blob",
                    "text": "* @owner\n",
                    "isTruncated": False,
                }
            }
        }
        text = client.get_repository_file_content(
            self.ORG, "Asana", "codez", "next-master", "CODEOWNERS"
        )
        self.assertEqual(text, "* @owner\n")
        mock_query.assert_called_once_with(
            self.ORG,
            GetRepositoryFileContent,
            {"owner": "Asana", "name": "codez", "expression": "next-master:CODEOWNERS"},
        )

    def test_missing_file_returns_none(self, mock_query):
        mock_query.return_value = {"repository": {"object": None}}
        self.assertIsNone(
            client.get_repository_file_content(
                self.ORG, "Asana", "codez", "next-master", "docs/CODEOWNERS"
            )
        )

    def test_truncated_file_raises(self, mock_query):
        mock_query.return_value = {
            "repository": {
                "object": {"__typename": "Blob", "text": "partial", "isTruncated": True}
            }
        }
        with self.assertRaises(ValueError):
            client.get_repository_file_content(
                self.ORG, "Asana", "codez", "next-master", "CODEOWNERS"
            )


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
