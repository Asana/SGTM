import hashlib
import hmac
import json

from src.github.models import HttpResponse
from src.config import GITHUB_HMAC_SECRET
import src.github.webhook as github_webhook


def handler(event: dict, context: dict) -> HttpResponse:
    if "headers" not in event:
        return HttpResponse(
            {
                "statusCode": "400",
                "body": "Expected there to be headers in the event. Keys were: {}".format(
                    event.keys()
                ),
            }
        )

    event_type = event["headers"].get("X-GitHub-Event")
    signature = event["headers"].get("X-Hub-Signature")

    if GITHUB_HMAC_SECRET is None:
        return HttpResponse({"statusCode": "400", "body": "GITHUB_HMAC_SECRET"})
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
        return HttpResponse({"statusCode": "501"})

    if not event_type:
        return HttpResponse(
            {
                "statusCode": "400",
                "body": "Expected a X-GitHub-Event header, but none found",
            }
        )

    github_event = json.loads(event["body"])
    try:
        return github_webhook.handle_github_webhook(event_type, github_event)
    except Exception as error:
        return HttpResponse({"statusCode": "500", "body": error})
