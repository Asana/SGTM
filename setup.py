from __future__ import print_function
import boto3
import json
import os
import sys


def main():

    # Setup terraform backend S3 bucket
    bucket_name = "sgtm-terraform-state-bucket"
    table_name = "sgtm_terraform_state_lock"

    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(
        ACL="private", Bucket=bucket_name,
    )

    client.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={"MFADelete": "Disabled", "Status": "Enabled"},
    )

    client.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )

    # Setup DynamoDB table
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.create_table(
        AttributeDefinitions=[{"AttributeName": "LockID", "AttributeType": "S"},],
        TableName=table_name,
        KeySchema=[{"AttributeName": "LockID", "KeyType": "HASH"},],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )


if __name__ == "__main__":
    main()
