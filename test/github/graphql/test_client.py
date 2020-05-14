from unittest.mock import patch, Mock
from src.github.graphql import client
from test.impl.base_test_case_class import BaseClass


@patch.object(client, '_execute_graphql_query')
class TestGithubClientGetReviewForDatabaseId(BaseClass):

    def test_when_no_pull_request_found(self, mock_query):
        mock_query.return_value = {"node": {"reviews": {"edges": []}}}
        with self.assertRaises(ValueError):
            actual = client.get_review_for_database_id('jij', 'ajijj')


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
