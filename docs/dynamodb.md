# Dynamodb in SGTM

This is an overview of how SGTM interacts with Dynamodb.

## Tables

#### sgtm-lock
A table containing all locks for current SGTM processes. Locks are a GitHub node id, currently either PR id or issue comment id.

We can receive multiple GitHub webhooks at once for the same GitHub object. To avoid race conditions from handling the webhooks in parallel, we lock on GitHub objects with the same id.

To lock operations, use the `dynamodb_lock` helper:
```
from src.dynamodb.lock import dynamodb_lock

with dynamodb_lock(pull_request_id):
    ...
```

#### sgtm-objects
A mapping of GitHub objects (github node id) to Asana objects (asana gid).

For example:
* GitHub repository -> Asana project
* GitHub PR -> Asana task
* Github Comment / Review Comment -> Asana comment

All Asana objects created or used by SGTM should be tracked in this table. When handling incoming webhooks, SGTM will fetch relevant objects to update if they exist, otherwise create a new object and add it to the table.

#### sgtm-users
A mapping of GitHub users (github handle string) to Asana users (asana user id string).

This table is read by SGTM to convert GitHub users to corresponding Asana users. The mapping is currently kept updated via [a lambda](/src/sync_users/handler.py). Webhook events handled by SGTM should never write to this table.
