from datetime import timedelta
from python_dynamodb_lock.python_dynamodb_lock import DynamoDBLockError
from test.impl.mock_dynamodb_test_case import MockDynamoDbTestCase
from src.dynamodb.lock import dynamodb_lock


class DynamodbLockTest(MockDynamoDbTestCase):
    def test_dynamodb_lock_different_pull_request_ids(self):
        dummy_counter = 0
        with dynamodb_lock("pull_request_1"):
            dummy_counter += 1
            with dynamodb_lock("pull_request_2"):
                dummy_counter += 1

        self.assertEqual(dummy_counter, 2)

    def test_dynamodb_lock_consecutive_same_lock(self):
        # Just make sure the lock is released properly after the block
        lock_name = "pull_request_id"
        dummy_counter = 0
        with dynamodb_lock(lock_name):
            dummy_counter += 1

        with dynamodb_lock(lock_name):
            dummy_counter += 1

        self.assertEqual(dummy_counter, 2)

    def test_dynamodb_lock_raises_exception_thrown_in_block(self):
        class DemoException(Exception):
            pass

        lock_name = "pull_request_id"

        with self.assertRaises(DemoException):
            with dynamodb_lock(lock_name):
                raise DemoException("oops")

        # Lock should still be released after the exception was raised
        dummy_counter = 0
        with dynamodb_lock(lock_name):
            dummy_counter += 1
        self.assertEqual(dummy_counter, 1)

    def test_dynamodb_lock_blocks_others_from_acquiring_lock(self):
        lock_name = "pull_request_id"
        dummy_counter = 0
        with dynamodb_lock(lock_name):
            dummy_counter += 1
            with self.assertRaises(DynamoDBLockError):
                with dynamodb_lock(
                    lock_name, retry_timeout=timedelta(milliseconds=0.001)
                ):  # same lock name
                    dummy_counter += 1

        self.assertEqual(dummy_counter, 1)


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
