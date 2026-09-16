# Dynamodb in SGTM

This is an overview of how SGTM interacts with Dynamodb.

## Tables

#### sgtm-lock
A table containing all locks for current SGTM processes. Locks are a GitHub node id, currently either PR id or issue comment id.

We can receive multiple GitHub webhooks at once for the same GitHub object. To avoid race conditions from handling the webhooks in parallel, we lock on GitHub objects with the same id.

To lock operations, use the `lock_client`:
```
from src.aws.lock import dynamodb_lock_client

with dynamodb_lock_client.acquire_lock(pull_request_id, sort_key=pull_request_id):
    ...
```

#### sgtm-objects
A mapping of GitHub objects (github node id) to Asana objects (asana gid).

For example:
* GitHub repository -> Asana project
* GitHub PR -> Asana task
* Github Comment / Review Comment -> Asana comment

All Asana objects created or used by SGTM should be tracked in this table. When handling incoming webhooks, SGTM will fetch relevant objects to update if they exist, otherwise create a new object and add it to the table.

The table also holds small per-PR JSON documents for features that need more than one id, stored in the `asana-id` attribute under a synthetic key of the form `<github node id>#<purpose>` so they never collide with real node ids. Today that is `<PR node id>#codeowners` for the [codeowner tasks](codeowner_tasks.md) feature; see `get_json_document` / `put_json_document` in `src/aws/dynamodb_client.py`.
