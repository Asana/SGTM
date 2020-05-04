import unittest

import src.github.webhook as github_webhook


class GithubWebhookTest(unittest.TestCase):
    def test_handle_github_webhook_501_error_for_unknown_event_type(self):
        response = github_webhook.handle_github_webhook("unknown_event_type", {})

        self.assertEqual(response.status_code(), "501")


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
