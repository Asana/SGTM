import json
from python_dynamodb_lock.python_dynamodb_lock import DynamoDBLockError  # type: ignore
from unittest.mock import patch

from src.handler import handle_github_webhook
from test.impl.base_test_case_class import BaseClass
from test.impl.mock_sqs_test_case import MockSQSTestCase

WEBHOOK_BODY_TEMPLATE = {
    "action": "edited",
    "comment": {"node_id": "hijkl"},
    "issue": {"node_id": "ksjklsdf"},
    "pull_request": {"node_id": "abcde"},
}


class TestHandleGithubWebhook(BaseClass):
    def test_validate_headers(self):
        response = handle_github_webhook(None, None, None)
        self.assertEqual(response["statusCode"], "400")

    @patch("src.dynamodb.lock.lock_client.acquire_lock")
    def test_swallows_dynamodb_lock_error(self, _mock_lock):
        _mock_lock.side_effect = DynamoDBLockError("error")
        response = handle_github_webhook(
            event_type="pull_request",
            delivery_id="123",
            webhook_body=json.dumps(WEBHOOK_BODY_TEMPLATE),
            should_retry=False,
        )

        self.assertEqual(response["statusCode"], "500")
        self.assertEqual(response["body"], "DynamoDBLockError: error - Unknown error")

    def test_throws_all_other_errors(self):
        response = handle_github_webhook(
            event_type="not_found",
            delivery_id="123",
            webhook_body=json.dumps(WEBHOOK_BODY_TEMPLATE),
            should_retry=False,
        )

        self.assertEqual(response["statusCode"], "501")
        self.assertEqual(response["body"], "No handler for event type not_found")

        with patch("src.github.webhook.handle_github_webhook") as mock:
            mock.side_effect = Exception("error")
            response = handle_github_webhook(
                event_type="pull_request",
                delivery_id="123",
                webhook_body=json.dumps(WEBHOOK_BODY_TEMPLATE),
                should_retry=False,
            )

        self.assertEqual(response["statusCode"], "500")
        self.assertEqual(response["body"], "error")


class TestSQSRequeue(MockSQSTestCase):
    @patch("src.dynamodb.lock.lock_client.acquire_lock")
    def test_requeue_on_error(self, _mock_lock):
        _mock_lock.side_effect = DynamoDBLockError("error")
        with patch("src.handler.SQS_URL", self.test_queue_url):
            response = handle_github_webhook(
                event_type="pull_request",
                delivery_id="123",
                webhook_body=json.dumps(WEBHOOK_BODY_TEMPLATE),
                should_retry=True,
            )

        self.assertEqual(response["statusCode"], "500")

        messages = self.client.receive_message(QueueUrl=self.test_queue_url)["Messages"]

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["Body"], json.dumps(WEBHOOK_BODY_TEMPLATE))


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
