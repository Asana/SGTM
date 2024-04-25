import hashlib
import hmac
import json
import traceback

from typing import Dict
from src.http import HttpResponse, HttpResponseDict
from src.config import GITHUB_HMAC_SECRET
from src.logger import logger
import src.github.webhook as github_webhook


def handler(event: dict, context: dict) -> HttpResponseDict:
    if "Records" in event:
        # SQS event
        batch_item_failures = []
        sqs_batch_response = {}
        for record in event["Records"]:
            webhook_headers = record["messageAttributes"]
            webhook_body = record["body"]
            logger.info(r"body:{}".format(webhook_body))

            event_type = webhook_headers.get("X-GitHub-Event").get("stringValue")
            signature = webhook_headers.get("X-Hub-Signature-256").get("stringValue")
            delivery_id = webhook_headers.get("X-GitHub-Delivery").get("stringValue")
            logger.info(f"Webhook delivery id: {delivery_id}")
            if not event_type:
                logger.error("X-GitHub-Event header not found")
                return HttpResponse(
                    "400", "Expected a X-GitHub-Event header, but none found"
                ).to_dict()

            if GITHUB_HMAC_SECRET is None:
                logger.error("GITHUB_HMAC_SECRET is not set")
                return HttpResponse("400", "GITHUB_HMAC_SECRET").to_dict()
            secret: str = GITHUB_HMAC_SECRET

            generated_signature = (
                "sha256="
                + hmac.new(
                    bytes(secret, "utf-8"),
                    msg=bytes(webhook_body, "utf-8"),
                    digestmod=hashlib.sha256,
                ).hexdigest()
            )
            if not hmac.compare_digest(generated_signature, signature):
                logger.error("HMAC signature mismatch, generated {}  expected {}". format(generated_signature, signature))
                return HttpResponse("501").to_dict()

            try:
                webhook_body_json = json.loads(webhook_body)
                http_response = github_webhook.handle_github_webhook(event_type, webhook_body_json)
                return http_response.to_dict()
            except Exception as _:
                # retry failures
                logger.error(traceback.format_exc())
                batch_item_failures.append({"itemIdentifier": record["messageId"]})
                sqs_batch_response["batchItemFailures"] = batch_item_failures
                return sqs_batch_response
        logger.error("No valid records found in the event")
        return HttpResponse("400", "Unknown event type, event: {}".format(event)).to_dict()
