import os
import boto3  # type: ignore
import json

# This config file sets the values of various configuration variables that
# SGTM's source code depends on. This file runs within the lambda itself, and
# relies on the env vars that Terraform sets in the `environment` block of the
# `aws_lambda_function.sgtm` resource.


ENV = os.getenv("ENV", "dev")
AWS_REGION = os.getenv("AWS_REGION")
LOCK_TABLE = os.getenv("LOCK_TABLE", "sgtm-lock")
OBJECTS_TABLE = os.getenv("OBJECTS_TABLE", "sgtm-objects")
GITHUB_USERNAMES_TO_ASANA_GIDS_S3_PATH = os.getenv(
    "GITHUB_USERNAMES_TO_ASANA_GIDS_S3_PATH",
)
SQS_URL = os.getenv("SQS_URL")
GITHUB_APP_NAME = os.getenv("GITHUB_APP_NAME", None)
GITHUB_APP_INSTALLATION_ACCESS_TOKEN_RETRIEVAL_URL = os.getenv(
    "GITHUB_APP_INSTALLATION_ACCESS_TOKEN_RETRIEVAL_URL", None
)


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
SGTM_FEATURE__ALLOW_PERSISTENT_TASK_ASSIGNEE = is_feature_flag_enabled(
    "SGTM_FEATURE__ALLOW_PERSISTENT_TASK_ASSIGNEE"
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
SGTM_FEATURE__CHECK_RERUN_ON_APPROVAL_ENABLED = is_feature_flag_enabled(
    "SGTM_FEATURE__CHECK_RERUN_ON_APPROVAL_ENABLED"
)


#### Particularly sensitive variables are retrieved from an S3 bucket, instead of
# from terraform-set environment variables. When SGTM is being manually tested,
# we retrieve the values of these variables from the environment, and expect
# that the user who is running the tests has set these environment variables.

__api_keys_s3_bucket = os.getenv("API_KEYS_S3_BUCKET")
__api_keys_s3_key = os.getenv("API_KEYS_S3_KEY")
if ENV == "test":
    # This means that we are running in a test environment, and we should
    # use dummy values
    LOG_LEVEL = "CRITICAL"
    AWS_REGION = "us-east-1"
    ASANA_API_KEY = "asana-test-key"
    GITHUB_API_KEY = "github-test-key"
    GITHUB_HMAC_SECRET = "github-test-secret"
elif __api_keys_s3_bucket and __api_keys_s3_key:
    # This means that we are running in a production environment, and we should
    # retrieve the API keys from the S3 bucket.
    LOG_LEVEL = "INFO"
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=__api_keys_s3_bucket, Key=__api_keys_s3_key)
    keys = json.loads(obj["Body"].read())
    ASANA_API_KEY = keys.get("ASANA_API_KEY", "")
    GITHUB_API_KEY = keys.get("GITHUB_API_KEY", "")
    GITHUB_HMAC_SECRET = keys.get("GITHUB_HMAC_SECRET", "")
else:
    LOG_LEVEL = "DEBUG"
    # This means that we are running in a local environment, and we should
    # retrieve the API keys from the environment.
    ASANA_API_KEY = os.getenv("ASANA_API_KEY", "")
    GITHUB_API_KEY = os.getenv("GITHUB_API_KEY", "")
    GITHUB_HMAC_SECRET = os.getenv("GITHUB_HMAC_SECRET", "")
