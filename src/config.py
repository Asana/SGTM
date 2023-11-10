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
ASANA_USERS_PROJECT_ID = os.getenv("ASANA_USERS_PROJECT_ID", "")


# Feature flags
def is_feature_flag_enabled(flag_name: str) -> bool:
    return os.getenv(flag_name) == "true"


SGTM_FEATURE__AUTOCOMPLETE_ENABLED = is_feature_flag_enabled(
    "SGTM_FEATURE__AUTOCOMPLETE_ENABLED"
)
SGTM_FEATURE__AUTOMERGE_ENABLED = is_feature_flag_enabled(
    "SGTM_FEATURE__AUTOMERGE_ENABLED"
)
SGTM_FEATURE__DISABLE_GITHUB_TEAM_SUBSCRIPTION = is_feature_flag_enabled(
    "SGTM_FEATURE__DISABLE_GITHUB_TEAM_SUBSCRIPTION"
)
SGTM_FEATURE__TASK_ASSIGNEE_IS_ALWAYS_PR_CREATOR = is_feature_flag_enabled(
    "SGTM_FEATURE__TASK_ASSIGNEE_IS_ALWAYS_PR_CREATOR"
)
SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS = {
    github_username
    for github_username in os.getenv(
        "SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS", ""
    ).split(",")
    if github_username
}
SGTM_FEATURE__CHECK_RERUN_THRESHOLD_HOURS = int(
    os.getenv("SGTM_FEATURE__CHECK_RERUN_THRESHOLD_HOURS", "0")
)
SGTM_FEATURE__CHECK_RERUN_BASE_REF_NAMES = {
    base_ref
    for base_ref in os.getenv(
        "SGTM_FEATURE__CHECK_RERUN_BASE_REF_NAMES", "main,master"
    ).split(",")
    if base_ref
}
