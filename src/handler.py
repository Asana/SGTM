import hashlib
import hmac
import json
import traceback
from python_dynamodb_lock.python_dynamodb_lock import DynamoDBLockError  # type: ignore

import src.aws.sqs_client as sqs_client
import src.github.webhook as github_webhook
from src.config import GITHUB_HMAC_SECRET
from src.http import HttpResponse, HttpResponseDict
from src.logger import logger


def handle_github_webhook(event_type: str, webhook_body: str) -> HttpResponseDict:
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
        if http_response is None: # handle_github_webhook can occasionally return None
            http_response = HttpResponse("500", "Unknown error")
        return http_response.to_dict()


def handler(event: dict, context: dict) -> HttpResponseDict:
    if "Records" in event:
        logger.info(f"{len(event['Records'])} Records: {event['Records']}")
        # SQS event
        assert len(event["Records"]) == 1
        record = event["Records"][0]
        event_type = (
            record.get("messageAttributes").get("X-GitHub-Event").get("stringValue")
        )
        return handle_github_webhook(event_type, record["body"])

    if "headers" in event:
        # API Gateway event
        if GITHUB_HMAC_SECRET is None:
            return HttpResponse("400", "GITHUB_HMAC_SECRET").to_dict()

        secret: str = GITHUB_HMAC_SECRET
        event_type = event["headers"].get("X-GitHub-Event")
        signature = event["headers"].get("X-Hub-Signature")
        event_body = event["body"]

        generated_signature = (
            "sha1="
            + hmac.new(
                bytes(secret, "utf-8"),
                msg=bytes(event_body, "utf-8"),
                digestmod=hashlib.sha1,
            ).hexdigest()
        )
        if not hmac.compare_digest(generated_signature, signature):
            return HttpResponse("501").to_dict()

        response = handle_github_webhook(event_type, event_body)
        if response["statusCode"] == "500":
            sqs_client.queue_new_event(event_type, event_body)
        return response

    error_message = "Unknown event type, event: {}".format(event)
    logger.error(error_message)
    return HttpResponse("400", error_message).to_dict()
