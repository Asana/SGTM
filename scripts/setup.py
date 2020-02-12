from __future__ import print_function
import argparse
import boto3
from io import BytesIO
import json
import os
import sys

REGION = "us-east-1"


s3_client = boto3.client("s3", region_name=REGION)


def set_api_keys():
    user_input = input("Have you ran `terraform apply` yet? (type y/n): ")
    if user_input != "y":
        print(
            "Operation cancelled: Run set up your infrastructure with terraform first"
        )
        return

    github_api_key = input("Enter your github api key: ")
    asana_api_key = input("Enter your asana api key: ")

    keys = {"ASANA_API_KEY": asana_api_key, "GITHUB_API_KEY": github_api_key}

    directory = os.path.dirname(__file__)
    file_name = os.path.join(directory, "../terraform/terraform.tfvars.json")

    # Get bucket name
    with open(file_name) as f:
        obj = json.load(f)
        bucket_name = obj["api_key_s3_bucket_name"]
        key_name = obj["api_key_s3_object"]

    s3_client.put_object(
        Body=bytes(json.dumps(keys).encode("UTF-8")), Bucket=bucket_name, Key=key_name
    )


def setup_state():
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

    # Setup DynamoDB table
    client = boto3.client("dynamodb", region_name=REGION)
    client.create_table(
        AttributeDefinitions=[{"AttributeName": "LockID", "AttributeType": "S"},],
        TableName=table_name,
        KeySchema=[{"AttributeName": "LockID", "KeyType": "HASH"},],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )


COMMAND_MAP = {"state": setup_state, "api-keys": set_api_keys}


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Set up actions for SGTM")
    arg_parser.add_argument(
        "action",
        type=str,
        choices=["state", "api-keys"],
        help="Select which setup action to perform.",
    )

    args = arg_parser.parse_args()
    COMMAND_MAP[args.action]()
