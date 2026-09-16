import json
import os
from unittest.mock import patch

import boto3  # type: ignore
from moto import mock_s3  # type: ignore

import src.aws.s3_client as s3_client
from src.aws.s3_client import (
    CodeownerTasksOptInList,
    parse_codeowner_tasks_opt_in_document,
)
from src.config import AWS_REGION
from test.impl.base_test_case_class import BaseClass

os.environ.setdefault("AWS_ACCESS_KEY_ID", "foobar_key")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "foobar_secret")

BUCKET = "asana-sgtm-custom-config"
KEY = "codeowner_tasks_opt_in.json"


class TestParseOptInDocument(BaseClass):
    def test_list_shape(self):
        self.assertEqual(parse_codeowner_tasks_opt_in_document(["a", "b"]), {"a", "b"})

    def test_object_shape(self):
        document = {
            "version": 1,
            "opted_in": {
                "harshita-gupta": {"since": "2026-09-16", "asana_email": "h@x.com"},
                "skeggse": {"since": "2026-09-16"},
            },
        }
        self.assertEqual(
            parse_codeowner_tasks_opt_in_document(document),
            {"harshita-gupta", "skeggse"},
        )

    def test_unexpected_shape_is_empty(self):
        self.assertEqual(parse_codeowner_tasks_opt_in_document({"version": 1}), set())
        self.assertEqual(parse_codeowner_tasks_opt_in_document("nope"), set())


@mock_s3
class TestCodeownerTasksOptInList(BaseClass):
    def setUp(self):
        self.s3 = boto3.client("s3", region_name=AWS_REGION)
        self.s3.create_bucket(Bucket=BUCKET)

    def put(self, document):
        self.s3.put_object(Bucket=BUCKET, Key=KEY, Body=json.dumps(document))

    def test_reads_and_caches(self):
        self.put(["alice"])
        opt_in = CodeownerTasksOptInList(f"{BUCKET}/{KEY}")
        self.assertEqual(opt_in.logins(), {"alice"})

        # A change within the TTL is not seen yet...
        self.put(["alice", "bob"])
        self.assertEqual(opt_in.logins(), {"alice"})
        # ...and is picked up once the cache expires.
        opt_in._cached_at -= CodeownerTasksOptInList.CACHE_TTL_SECONDS + 1
        self.assertEqual(opt_in.logins(), {"alice", "bob"})

    def test_unconfigured_path_means_nobody(self):
        self.assertEqual(CodeownerTasksOptInList(None).logins(), set())
        self.assertEqual(CodeownerTasksOptInList("no-slash").logins(), set())

    def test_missing_object_means_nobody_but_keeps_last_good_copy(self):
        opt_in = CodeownerTasksOptInList(f"{BUCKET}/missing.json")
        self.assertEqual(opt_in.logins(), set())

        self.put(["alice"])
        cached = CodeownerTasksOptInList(f"{BUCKET}/{KEY}")
        self.assertEqual(cached.logins(), {"alice"})
        self.s3.delete_object(Bucket=BUCKET, Key=KEY)
        cached._cached_at -= CodeownerTasksOptInList.CACHE_TTL_SECONDS + 1
        self.assertEqual(cached.logins(), {"alice"})

    def test_module_helper_uses_singleton(self):
        self.put(["alice"])
        with patch.object(
            CodeownerTasksOptInList,
            "singleton",
            return_value=CodeownerTasksOptInList(f"{BUCKET}/{KEY}"),
        ):
            self.assertTrue(s3_client.is_opted_in_to_codeowner_tasks("alice"))
            self.assertFalse(s3_client.is_opted_in_to_codeowner_tasks("bob"))


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
