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
    if "headers" not in event:
        return HttpResponse(
            "400",
            "Expected there to be headers in the event. Keys were: {}".format(
                event.keys()
            ),
        ).to_dict()

    event_type = event["headers"].get("X-GitHub-Event")
    signature = event["headers"].get("X-Hub-Signature")
    delivery_id = event["headers"].get("X-GitHub-Delivery")
    logger.info(f"Webhook delivery id: {delivery_id}")

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

    if not event_type:
        return HttpResponse(
            "400", "Expected a X-GitHub-Event header, but none found"
        ).to_dict()

    github_event = json.loads(event["body"])
    try:
        http_response = github_webhook.handle_github_webhook(event_type, github_event)
        return http_response.to_dict()
    except Exception as error:
        logger.error(traceback.format_exc())
        return HttpResponse("500", str(error)).to_dict()
