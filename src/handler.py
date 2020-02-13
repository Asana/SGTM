import hashlib
import hmac
import json

from src.config import GITHUB_HMAC_SECRET
import src.github.webhook as github_webhook


def handler(event: dict, context: dict) -> None:
    if "headers" not in event:
        raise KeyError(
            "Expected there to be headers in the event. Keys were: {}".format(
                event.keys()
            )
        )

    # def verify_signature(payload_body)
    #   signature = 'sha1=' + OpenSSL::HMAC.hexdigest(OpenSSL::Digest.new('sha1'), ENV['SECRET_TOKEN'], payload_body)
    #   return halt 500, "Signatures didn't match!" unless Rack::Utils.secure_compare(signature, request.env['HTTP_X_HUB_SIGNATURE'])
    # end
    event_type = event["headers"].get("X-GitHub-Event")
    signature = event["headers"].get("X-Hub-Signature")

    generated_signature = (
        "sha1="
        + hmac.new(
            bytes(GITHUB_HMAC_SECRET, "utf-8"), digestmod=hashlib.sha1
        ).hexdigest()
    )

    if not hmac.compare_digest(generated_signature, signature):
        raise PermissionError

    if not event_type:
        raise KeyError("Expected a X-GitHub-Event header, but none found")

    github_event = json.loads(event["body"])
    return github_webhook.handle_github_webhook(event_type, github_event)
