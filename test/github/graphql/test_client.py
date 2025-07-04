from unittest.mock import patch, call
from src.github.graphql import client
from src.github.graphql.queries import (
    IterateReviewsForPullRequestId,
    IteratePullRequestIdsForCommitId,
    GetTeamMembers,
)
from test.impl.base_test_case_class import BaseClass


@patch.object(client, "_execute_graphql_query")
class TestGithubClientGetReviewForDatabaseId(BaseClass):
    ORG_NAME = "FooOrgnization"
    REVIEW_DB_ID = "1234566"
    PULL_REQUEST_ID = "PR_jiefjiejfji232--"

    def test_when_no_reviews_found__should_return_None(self, mock_query):
        mock_query.return_value = {"node": {"reviews": {"edges": []}}}

        actual = client.get_review_for_database_id(
            self.ORG_NAME, self.PULL_REQUEST_ID, self.REVIEW_DB_ID
        )

        self.assertEqual(actual, None)
        mock_query.assert_called_once_with(
            self.ORG_NAME,
            IterateReviewsForPullRequestId,
            {"pullRequestId": self.PULL_REQUEST_ID},
        )

    def test_when_no_reviews_match__should_return_None(self, mock_query):
        mock_query.side_effect = [
            {
                "node": {
                    "reviews": {
                        "edges": [
                            {
                                "cursor": "some-cursor",
                                "node": {"databaseId": "doesnt match"},
                            }
                        ]
                    }
                }
            },
            {"node": {"reviews": {"edges": []}}},
        ]

        actual = client.get_review_for_database_id(
            self.ORG_NAME, self.PULL_REQUEST_ID, self.REVIEW_DB_ID
        )

        self.assertEqual(actual, None)

        mock_query.assert_has_calls(
            [
                call(
                    self.ORG_NAME,
                    IterateReviewsForPullRequestId,
                    {"pullRequestId": self.PULL_REQUEST_ID},
                ),
                call(
                    self.ORG_NAME,
                    IterateReviewsForPullRequestId,
                    {"pullRequestId": self.PULL_REQUEST_ID, "cursor": "some-cursor"},
                ),
            ]
        )
        self.assertEqual(mock_query.call_count, 2)

    def test_when_review_in_first_batch_matches__should_return_it(self, mock_query):
        matching_node = {"id": "matching-review", "databaseId": self.REVIEW_DB_ID}
        other_node = {"id": "other-review", "databaseId": "doesnt match"}
        mock_query.side_effect = [
            {
                "node": {
                    "reviews": {
                        "edges": [
                            {"cursor": "some-cursor", "node": other_node},
                            {"cursor": "some-cursor", "node": matching_node},
                        ]
                    }
                }
            },
            {"node": {"reviews": {"edges": []}}},
        ]
        actual = client.get_review_for_database_id(
            self.ORG_NAME, self.PULL_REQUEST_ID, self.REVIEW_DB_ID
        )

        self.assertEqual(actual.id(), "matching-review")

        # Should onlly be called once, since the matching review is in the first batch returned by graphql.
        mock_query.assert_called_once_with(
            self.ORG_NAME,
            IterateReviewsForPullRequestId,
            {"pullRequestId": self.PULL_REQUEST_ID},
        )

    def test_when_review_in_second_batch_matches__should_return_it(self, mock_query):
        matching_node = {"id": "matching-review", "databaseId": self.REVIEW_DB_ID}
        other_node = {"id": "other-review", "databaseId": "doesnt match"}
        mock_query.side_effect = [
            {
                "node": {
                    "reviews": {"edges": [{"cursor": "cursor-1", "node": other_node}]}
                }
            },
            {
                "node": {
                    "reviews": {
                        "edges": [{"cursor": "cursor-2", "node": matching_node}]
                    }
                }
            },
            {"node": {"reviews": {"edges": []}}},
        ]
        actual = client.get_review_for_database_id(
            self.ORG_NAME, self.PULL_REQUEST_ID, self.REVIEW_DB_ID
        )

        self.assertEqual(actual.id(), "matching-review")

        # Should onlly be called twice, since the matching review is in the first batch returned by graphql.
        mock_query.assert_has_calls(
            [
                call(
                    self.ORG_NAME,
                    IterateReviewsForPullRequestId,
                    {"pullRequestId": self.PULL_REQUEST_ID},
                ),
                call(
                    self.ORG_NAME,
                    IterateReviewsForPullRequestId,
                    {"pullRequestId": self.PULL_REQUEST_ID, "cursor": "cursor-1"},
                ),
            ]
        )
        self.assertEqual(mock_query.call_count, 2)


@patch.object(client, "_execute_graphql_query")
class TestGithubClientGetPullRequestForCommitId(BaseClass):
    COMMIT_ID = "C_jiefjiejfji232--"
    ORG_NAME = "BarOrganization"

    def test_no_pull_requests_found_should_return_none(self, mock_query):
        mock_query.return_value = {"commit": {"associatedPullRequests": {"edges": []}}}

        actual = client.get_pull_request_for_commit_id(
            self.ORG_NAME,
            self.COMMIT_ID,
        )

        self.assertEqual(actual, None)
        mock_query.assert_called_once_with(
            self.ORG_NAME,
            IteratePullRequestIdsForCommitId,
            {"commitId": self.COMMIT_ID},
        )

    def test_pull_requests_not_last_commit_should_return_none(self, mock_query):
        mock_query.side_effect = [
            {
                "commit": {
                    "associatedPullRequests": {
                        "edges": [
                            {
                                "cursor": "some-cursor",
                                "node": {
                                    "id": "some-id",
                                    "commits": {
                                        "nodes": [{"commit": {"id": "last-commit"}}]
                                    },
                                },
                            }
                        ]
                    }
                }
            },
            {"commit": {"associatedPullRequests": {"edges": []}}},
        ]

        actual = client.get_pull_request_for_commit_id(
            self.ORG_NAME,
            self.COMMIT_ID,
        )

        self.assertEqual(actual, None)
        mock_query.assert_has_calls(
            [
                call(
                    self.ORG_NAME,
                    IteratePullRequestIdsForCommitId,
                    {"commitId": self.COMMIT_ID},
                ),
                call(
                    self.ORG_NAME,
                    IteratePullRequestIdsForCommitId,
                    {"commitId": self.COMMIT_ID, "cursor": "some-cursor"},
                ),
            ]
        )

    @patch.object(client, "get_pull_request")
    def test_pull_requests_match_last_commit_should_return_first(
        self, mock_get_pull_request, mock_query
    ):
        other_node = {"id": "pr-1", "commits": {"nodes": [{"commit": {"id": "other"}}]}}
        matching_node = {
            "id": "some-id",
            "commits": {"nodes": [{"commit": {"id": self.COMMIT_ID}}]},
        }
        mock_query.side_effect = [
            {
                "commit": {
                    "associatedPullRequests": {
                        "edges": [
                            {
                                "cursor": "cursor-1",
                                "node": other_node,
                            },
                            {
                                "cursor": "cursor-2",
                                "node": matching_node,
                            },
                            {
                                "cursor": "cursor-3",
                                "node": matching_node,
                            },
                        ]
                    }
                }
            },
        ]
        mock_get_pull_request.return_value = None

        _ = client.get_pull_request_for_commit_id(
            self.ORG_NAME,
            self.COMMIT_ID,
        )

        mock_query.assert_called_once_with(
            self.ORG_NAME,
            IteratePullRequestIdsForCommitId,
            {"commitId": self.COMMIT_ID},
        )
        mock_get_pull_request.assert_called_once_with(
            self.ORG_NAME, matching_node["id"]
        )


@patch.object(client, "_execute_graphql_query")
class TestGithubClientGetTeamMembers(BaseClass):
    def test_get_team_members_success(self, mock_query):
        mock_query.return_value = {
            "organization": {
                "team": {
                    "members": {
                        "nodes": [
                            {"login": "user1"},
                            {"login": "user2"},
                            {"login": "user3"},
                        ]
                    }
                }
            }
        }

        actual = client.get_team_members("test-org", "test-team")

        self.assertEqual(["user1", "user2", "user3"], actual)
        mock_query.assert_called_once_with(
            "test-org",
            GetTeamMembers.GetTeamMembers,
            {"org": "test-org", "teamSlug": "test-team"},
        )

    def test_get_team_members_no_team(self, mock_query):
        mock_query.return_value = {"organization": {"team": None}}

        actual = client.get_team_members("test-org", "non-existent-team")

        self.assertEqual([], actual)
        mock_query.assert_called_once_with(
            "test-org",
            GetTeamMembers.GetTeamMembers,
            {"org": "test-org", "teamSlug": "non-existent-team"},
        )

    def test_get_team_members_empty_team(self, mock_query):
        mock_query.return_value = {"organization": {"team": {"members": {"nodes": []}}}}

        actual = client.get_team_members("test-org", "empty-team")

        self.assertEqual([], actual)
        mock_query.assert_called_once_with(
            "test-org",
            GetTeamMembers.GetTeamMembers,
            {"org": "test-org", "teamSlug": "empty-team"},
        )


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
