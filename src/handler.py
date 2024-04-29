import hashlib
import hmac
import json
import traceback
import boto3

from src.http import HttpResponse, HttpResponseDict
from src.config import GITHUB_HMAC_SECRET, SQS_URL
from src.logger import logger
import src.github.webhook as github_webhook

def handle_github_webhook(event_type: str, delivery_id: str, github_event: dict, should_retry: bool = False) -> HttpResponse:
    logger.info(f"Webhook delivery id: {delivery_id}")

    if not event_type:
        logger.error("X-GitHub-Event header not found")
        return HttpResponse(
            "400", "Expected a X-GitHub-Event header, but none found"
        ).to_dict()

    try:
        http_response = github_webhook.handle_github_webhook(event_type, github_event)
        return http_response.to_dict()
    except Exception as error:
        logger.error(traceback.format_exc())
        if should_retry:
            logger.info("Sending webhook to SQS")
            # retry failures
            sqs = boto3.client('sqs')
            sqs.send_message(
                QueueUrl=SQS_URL,
                MessageBody=github_event,
                MessageGroupId=delivery_id,
                MessageAttributes={
                    "X-GitHub-Event": {
                        "DataType": "String",
                        "StringValue": event_type
                    },
                    "X-GitHub-Delivery": {
                        "DataType": "String",
                        "StringValue": delivery_id
                    }
                }
            )
        return HttpResponse("500", str(error)).to_dict()

def handler(event: dict, context: dict) -> HttpResponseDict:
    if "Records" in event:
        logger.info(f"Records: {event['Records']}")
        # SQS event
        for record in event["Records"]:
            webhook_headers = record["messageAttributes"]
            event_type = webhook_headers.get("X-GitHub-Event").get("stringValue")
            delivery_id = webhook_headers.get("X-GitHub-Delivery").get("stringValue")
            github_event = json.loads(record["body"])
            handle_github_webhook(event_type, delivery_id, github_event)
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

        github_event = json.loads(event["body"])
        handle_github_webhook(event_type, delivery_id, github_event, should_retry=True)


    error_message = "Unknown event type, event: {}".format(event)
    logger.error(error_message)
    return HttpResponse("400", error_message).to_dict()
