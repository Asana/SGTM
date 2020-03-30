from __future__ import print_function
import argparse
from io import BytesIO
import json
import os
import sys

import boto3  # type: ignore
import botocore

REGION = "us-east-1"
# TODO: REGION should not be hardcoded

s3_client = boto3.client("s3", region_name=REGION)


def set_api_keys(args):
    user_input = input("Have you ran `terraform apply` yet? (type y/n): ")
    if user_input != "y":
        print(
            "Operation cancelled: Run set up your infrastructure with terraform first"
        )
        return

    # Get bucket name and key name
    directory = os.path.dirname(__file__)
    file_name = os.path.join(directory, "../terraform/terraform.tfvars.json")
    with open(file_name) as f:
        obj = json.load(f)
        bucket_name = obj["api_key_s3_bucket_name"]
        key_name = obj["api_key_s3_object"]

    keys = {}
    try:
        obj = s3_client.get_object(Bucket=bucket_name, Key=key_name)
        keys = json.loads(obj["Body"].read())
    except botocore.exceptions.ClientError:
        # The key file exist doesn't yet
        pass

    for secret_name in args.keys:
        secret = input(
            "Enter the secret for {} (press enter without typing to skip): ".format(
                secret_name
            )
        )
        if secret != "":
            keys[secret_name] = secret

    s3_client.put_object(
        Body=bytes(json.dumps(keys).encode("UTF-8")), Bucket=bucket_name, Key=key_name
    )


def setup_state(args):
    # Setup terraform backend S3 bucket
    bucket_name = "sgtm-terraform-state-bucket"
    table_name = "sgtm_terraform_state_lock"

    s3_client = boto3.client("s3", region_name=REGION)
    s3_client.create_bucket(
        ACL="private", Bucket=bucket_name,
    )

    s3_client.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={"MFADelete": "Disabled", "Status": "Enabled"},
    )

    s3_client.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )

    # Setup DynamoDB table #DynamoDbSchema
    client = boto3.client("dynamodb", region_name=REGION)
    client.create_table(
        AttributeDefinitions=[{"AttributeName": "LockID", "AttributeType": "S"},],
        TableName=table_name,
        KeySchema=[{"AttributeName": "LockID", "KeyType": "HASH"},],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )


COMMAND_MAP = {"state": setup_state, "secrets": set_api_keys}


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Set up actions for SGTM")
    subparsers = arg_parser.add_subparsers()

    parser_state = subparsers.add_parser("state", help="Set up state")
    parser_state.set_defaults(action="state")

    parser_secrets = subparsers.add_parser(
        "secrets", help="Add api keys and secrets for SGTM to use"
    )
    parser_secrets.set_defaults(action="secrets")
    parser_secrets.add_argument(
        "--keys",
        default=("ASANA_API_KEY", "GITHUB_API_KEY", "GITHUB_HMAC_SECRET"),
        choices=("ASANA_API_KEY", "GITHUB_API_KEY", "GITHUB_HMAC_SECRET"),
        help="Select which secret to change",
        nargs="+",
    )

    args = arg_parser.parse_args()
    COMMAND_MAP[args.action](args)
