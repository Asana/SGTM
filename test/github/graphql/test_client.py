from unittest.mock import patch, Mock, call
from src.github.graphql import client
from test.impl.base_test_case_class import BaseClass


@patch.object(client, "_execute_graphql_query")
class TestGithubClientGetReviewForDatabaseId(BaseClass):
    REVIEW_DB_ID = "1234566"
    PULL_REQUEST_ID = "jiefjiejfji232--"

    def test_when_no_reviews_found__should_raise_error(self, mock_query):
        mock_query.return_value = {"node": {"reviews": {"edges": []}}}

        with self.assertRaises(ValueError):
            actual = client.get_review_for_database_id(
                self.PULL_REQUEST_ID, self.REVIEW_DB_ID
            )

        mock_query.assert_called_once_with(
            "IterateReviews", {"pullRequestId": self.PULL_REQUEST_ID}
        )

    def test_when_no_reviews_match__should_raise_error(self, mock_query):
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

        with self.assertRaises(ValueError):
            actual = client.get_review_for_database_id(
                self.PULL_REQUEST_ID, self.REVIEW_DB_ID
            )

        mock_query.assert_has_calls(
            [
                call("IterateReviews", {"pullRequestId": self.PULL_REQUEST_ID}),
                call(
                    "IterateReviews",
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
            self.PULL_REQUEST_ID, self.REVIEW_DB_ID
        )

        self.assertEqual(actual.id(), "matching-review")

        # Should onlly be called once, since the matching review is in the first batch returned by graphql.
        mock_query.assert_called_once_with(
            "IterateReviews", {"pullRequestId": self.PULL_REQUEST_ID}
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
            self.PULL_REQUEST_ID, self.REVIEW_DB_ID
        )

        self.assertEqual(actual.id(), "matching-review")

        # Should onlly be called twice, since the matching review is in the first batch returned by graphql.
        mock_query.assert_has_calls(
            [
                call("IterateReviews", {"pullRequestId": self.PULL_REQUEST_ID}),
                call(
                    "IterateReviews",
                    {"pullRequestId": self.PULL_REQUEST_ID, "cursor": "cursor-1"},
                ),
            ]
        )
        self.assertEqual(mock_query.call_count, 2)


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
