import os
import boto3  # type: ignore
import json

__api_keys_s3_bucket = os.getenv("API_KEYS_S3_BUCKET")
__api_keys_s3_key = os.getenv("API_KEYS_S3_KEY")
if __api_keys_s3_bucket is None or __api_keys_s3_key is None:
    ASANA_API_KEY = os.getenv("ASANA_API_KEY", "")
    GITHUB_API_KEY = os.getenv("GITHUB_API_KEY", "")
    GITHUB_HMAC_SECRET = os.getenv("GITHUB_HMAC_SECRET", "")
else:
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=__api_keys_s3_bucket, Key=__api_keys_s3_key)
    keys = json.loads(obj["Body"].read())
    ASANA_API_KEY = keys.get("ASANA_API_KEY", "")
    GITHUB_API_KEY = keys.get("GITHUB_API_KEY", "")
    GITHUB_HMAC_SECRET = keys.get("GITHUB_HMAC_SECRET", "")

ENV = os.getenv("ENV", "dev")
LOCK_TABLE = os.getenv("LOCK_TABLE", "sgtm-lock")
OBJECTS_TABLE = os.getenv("OBJECTS_TABLE", "sgtm-objects")
USERS_TABLE = os.getenv("USERS_TABLE", "sgtm-users")
