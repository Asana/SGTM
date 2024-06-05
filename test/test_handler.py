import json
import hmac
from python_dynamodb_lock.python_dynamodb_lock import DynamoDBLockError  # type: ignore
from unittest.mock import patch

import src.handler as handler
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
        response = handler.handle_github_webhook(None, None)
        self.assertEqual(response["statusCode"], "400")

    @patch("src.aws.lock.dynamodb_lock_client.acquire_lock")
    def test_swallows_dynamodb_lock_error(self, _mock_lock):
        _mock_lock.side_effect = DynamoDBLockError("error")
        response = handler.handle_github_webhook(
            event_type="pull_request",
            webhook_body=json.dumps(WEBHOOK_BODY_TEMPLATE),
        )

        self.assertEqual(response["statusCode"], "500")
        self.assertEqual(response["body"], "DynamoDBLockError: error - Unknown error")

    def test_throws_all_other_errors(self):
        response = handler.handle_github_webhook(
            event_type="not_found",
            webhook_body=json.dumps(WEBHOOK_BODY_TEMPLATE),
        )

        self.assertEqual(response["statusCode"], "501")
        self.assertEqual(response["body"], "No handler for event type not_found")

        with patch("src.github.webhook.handle_github_webhook") as mock:
            mock.side_effect = Exception("error")
            response = handler.handle_github_webhook(
                event_type="pull_request",
                webhook_body=json.dumps(WEBHOOK_BODY_TEMPLATE),
            )

        self.assertEqual(response["statusCode"], "500")
        self.assertEqual(response["body"], "error")


class TestSQSRequeue(MockSQSTestCase):
    @patch.object(hmac, "compare_digest", return_value=True)
    @patch("src.aws.lock.dynamodb_lock_client.acquire_lock")
    def test_requeue_on_error(self, _mock_lock, _mock_compare_digest):
        _mock_lock.side_effect = DynamoDBLockError("error")
        with patch("src.aws.sqs_client.SQS_URL", self.test_queue_url):
            response = handler.handler(
                event={
                    "headers": {
                        "X-GitHub-Event": "pull_request",
                        "X-Hub-Signature": "sha1=1234",
                    },
                    "body": json.dumps(WEBHOOK_BODY_TEMPLATE),
                },
                context={}
            )
        self.assertEqual(response["statusCode"], "500")

        messages = self.client.receive_message(QueueUrl=self.test_queue_url).get("Messages", [])

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["Body"], json.dumps(WEBHOOK_BODY_TEMPLATE))

    def test_no_requeue_for_sqs_event(self):
        response = handler.handler(
            event={
                "Records": [
                    {
                        "messageAttributes": {
                            "X-GitHub-Event": {"stringValue": None}
                        },
                        "body": json.dumps(WEBHOOK_BODY_TEMPLATE),
                    }
                ]
            },
            context={},
        )
        self.assertEqual(response["statusCode"], "400")

        messages = self.client.receive_message(QueueUrl=self.test_queue_url).get("Messages")
        self.assertIsNone(messages)



if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
