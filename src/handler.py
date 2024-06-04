import hashlib
import hmac
import json
import traceback
import boto3
from python_dynamodb_lock.python_dynamodb_lock import DynamoDBLockError  # type: ignore

import src.github.webhook as github_webhook
from src.config import GITHUB_HMAC_SECRET, SQS_URL, AWS_REGION
from src.http import HttpResponse, HttpResponseDict
from src.logger import logger


def handle_github_webhook(
    event_type: str, delivery_id: str, webhook_body: str, should_retry: bool = False
) -> HttpResponseDict:
    logger.info(f"Webhook delivery id: {delivery_id}")

    if not event_type:
        logger.error("X-GitHub-Event header not found")
        return HttpResponse(
            "400", "Expected a X-GitHub-Event header, but none found"
        ).to_dict()

    http_response = HttpResponse("501", "Unknown error")

    try:
        github_event = json.loads(webhook_body)
        http_response = github_webhook.handle_github_webhook(event_type, github_event)
    except DynamoDBLockError as dbe:
        logger.warning(f"Swallowing DynamoDBLockError: {dbe}")
        http_response = HttpResponse("500", str(dbe))
    except Exception as error:
        logger.error(traceback.format_exc())
        http_response = HttpResponse("500", str(error))
    finally:
        if should_retry and http_response.status_code == "500":
            logger.info("Sending webhook to SQS")
            # retry failures
            sqs = boto3.client("sqs", region_name=AWS_REGION)
            sqs.send_message(
                QueueUrl=SQS_URL,
                MessageBody=webhook_body,
                MessageGroupId=delivery_id,
                MessageAttributes={
                    "X-GitHub-Event": {"DataType": "String", "StringValue": event_type},
                    "X-GitHub-Delivery": {
                        "DataType": "String",
                        "StringValue": delivery_id,
                    },
                },
            )
        return http_response.to_dict()


def handler(event: dict, context: dict) -> HttpResponseDict:
    if "Records" in event:
        logger.info(f"Records: {event['Records']}")
        # SQS event
        for record in event["Records"]:
            webhook_headers = record["messageAttributes"]
            event_type = webhook_headers.get("X-GitHub-Event").get("stringValue")
            delivery_id = webhook_headers.get("X-GitHub-Delivery").get("stringValue")
            handle_github_webhook(event_type, delivery_id, record["body"])
        return HttpResponse("200").to_dict()

    if "headers" in event:
        # API Gateway event
        event_type = event["headers"].get("X-GitHub-Event")
        signature = event["headers"].get("X-Hub-Signature")
        delivery_id = event["headers"].get("X-GitHub-Delivery")

        if GITHUB_HMAC_SECRET is None:
            return HttpResponse("400", "GITHUB_HMAC_SECRET").to_dict()
        secret: str = GITHUB_HMAC_SECRET

        generated_signature = (
            "sha1="
            + hmac.new(
                bytes(secret, "utf-8"),
                msg=bytes(event["body"], "utf-8"),
                digestmod=hashlib.sha1,
            ).hexdigest()
        )
        if not hmac.compare_digest(generated_signature, signature):
            return HttpResponse("501").to_dict()

        return handle_github_webhook(
            event_type, delivery_id, event["body"], should_retry=True
        )

    error_message = "Unknown event type, event: {}".format(event)
    logger.error(error_message)
    return HttpResponse("400", error_message).to_dict()
