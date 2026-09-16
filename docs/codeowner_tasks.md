# Codeowner tasks

An opt-in SGTM feature for repositories that require [code owner](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners) approvals. When a pull request author adds a label, SGTM creates one Asana subtask per group of codeowners whose approval the PR needs, assigns each to an available codeowner, requests their review on GitHub, keeps the subtask's status in step with the PR, and routes the PR's Asana task between the codeowners and the author until every approval is in place.

Without this feature, GitHub's automatic codeowner review requests make every member of every requested team a follower of the PR's Asana task. With it, those automatic requests no longer add followers; the subtasks reach the right people instead.

- [What you see](#what-you-see)
  - [As a PR author](#as-a-pr-author)
  - [As a codeowner](#as-a-codeowner)
- [How SGTM decides](#how-sgtm-decides)
  - [Owner sets and subtasks](#owner-sets-and-subtasks)
  - [Subtask status](#subtask-status)
  - [Who a subtask is assigned to](#who-a-subtask-is-assigned-to)
  - [Who the PR is assigned to](#who-the-pr-is-assigned-to)
  - [Stacked pull requests](#stacked-pull-requests)
- [Setup](#setup)
- [Operations](#operations)

## What you see

### As a PR author

1. **Heads-up comment (opt-in).** If you opted in, SGTM comments on your PR as soon as it changes files that have codeowners: a table of those files and their owners, and what adding the label will do. The comment is updated as the set of codeowned files changes and is edited in place once you add the label. Authors who did not opt in see nothing until they add the label. The opt-in list is a JSON file in S3 (see [Setup](#setup)); your organization may provide a command for it, which the comments and task footers then name.
2. **The label.** When your PR is ready for codeowners, add the `assign-tasks-to-codeowners` label (configurable). SGTM creates the label in the repository the first time a PR there touches codeowned files. Draft PRs are ignored until they are marked ready for review; closed PRs are ignored.
3. **Confirmation.** SGTM edits its heads-up comment, or posts a new comment if you did not opt in, listing each subtask, who it is assigned to and why, with a link to the Asana subtask. It requests a review on GitHub from each assignee.
4. **Prefer a specific codeowner?** Request their review on GitHub, or reassign the Asana subtask to them. SGTM follows your choice and will not re-pick unless that person is out of office.
5. **The PR task** gains a 🛡️ checklist in its description (one line per owner set with status, assignee and a link to the subtask), a footer explaining where the tracking comes from, and the custom fields described below.

### As a codeowner

You receive an Asana subtask named `Codeowner review: #<number> - <PR title>` (with the owner set in parentheses when the PR needs several subtasks), plus a GitHub review request. The subtask description lists:

- the PR, its Asana task, the codeowners (any member can approve) and the author;
- the codeowner approval status and why;
- the codeowned files the PR changes, each linking to its diff with GitHub's *owned by you* filter applied, and marked with any other owners who could approve it instead;
- a link to only the files you own, and a link to the whole diff.

Approve the PR on GitHub on its latest commit; SGTM completes the subtask. It reopens the subtask, with a comment, if a later push dismisses your approval, if the PR changes codeowned files again after they had been dropped, or if a closed PR is reopened. It comments when it reassigns the subtask, when someone requests changes, when the PR merges without a codeowner approval and when the PR closes.

The subtask lives under the PR task and is also in the shared **codeowner PR approval tasks** project, which carries its custom fields:

| Field | Values |
| --- | --- |
| Codeowner Approval (SGTM) | Needed, Approved, Approval Stale, Changes Requested, No Longer Required, Merged with Bypass |
| Codeowners (SGTM) | the owner set, for example `platform, secdev` |
| PR Status, Author (SGTM), Branch Name (SGTM) | as on the PR task |

The PR task gets:

| Field | Values |
| --- | --- |
| Codeowner Review (SGTM) | Not Required (no codeowned files), Not Yet Requested (codeowned files, no label yet), Pending, Partially Approved, Approved, Changes Requested |
| Codeowners Pending (SGTM) | the owner sets still lacking approval |
| Review Status | gains **Needs Codeowner Approval**: the primary review is in, codeowner approvals are still missing |

## How SGTM decides

### Owner sets and subtasks

SGTM reads `CODEOWNERS` (from `.github/`, the repository root or `docs/`, in that order) on the branch GitHub evaluates the PR against and applies GitHub's matching rules: the last matching pattern wins, a pattern with no slash matches at any depth, a trailing slash means a directory. Every changed file that matches a rule with owners is a *codeowned file*, and the owners on its winning line are its *owner set*.

SGTM creates one subtask per distinct owner set on the PR, not per team, because GitHub needs one approval from any owner on the line, not one per team. When one owner set is a strict superset of another owner set on the same PR, its files are folded into the smaller set's subtask (an approval from the smaller set satisfies them too); the description marks those files with the other owners who could approve them.

The *pool* for an owner set is the union of its teams' members and its individual owners, minus the PR author. The author can never approve for their own files, so a subtask is created even when they are a codeowner.

### Subtask status

For each file, SGTM takes each pool member's latest approve / request-changes / dismissed review and applies GitHub's own rules: a request for changes from anyone in the pool blocks the file (**changes requested**) whatever others said; otherwise an approval from anyone in the pool makes it **approved**; otherwise a dismissed approval (a later push dismissed it) makes it **stale**; nothing → **needed**. A subtask's status is the worst of its files: Changes Requested, then Needed, then Approval Stale, then Approved. A PR that no longer changes any file of an owner set makes that subtask **No Longer Required** (completed, with a comment; it reopens if the files come back). A PR merged with a requirement still unapproved marks the subtask **Merged with Bypass**: informational, left open, completed if a codeowner approves the merged PR.

Reviews from users configured for follow-up review (`SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS`) never count.

### Who a subtask is assigned to

From the pool, minus anyone out of office in Asana and anyone without an Asana account mapping, SGTM prefers someone a person already asked to review, then someone who already reviewed or commented on the PR, then a random pick. When nobody is available the subtask is assigned to the PR author with a comment, and SGTM tries again on later events.

SGTM re-picks when the assignee is out of office, or after `SGTM_FEATURE__CODEOWNER_TASKS_IDLE_BUSINESS_DAYS` whole business days (Monday to Friday, UTC; default 1) without the assignee reviewing or commenting on the PR since being assigned: a subtask assigned on Friday at 15:00 UTC counts as idle from Monday 15:00 UTC, not Monday morning. It does not re-pick for idleness when a person chose the assignee: the author requested that codeowner's review on GitHub, or someone reassigned the subtask by hand in Asana (SGTM notices and adopts that choice). A requested codeowner who is out of office is not followed; if the current assignee goes out of office, SGTM falls back to its own pick even for a subtask a person had assigned.

### Who the PR is assigned to

The GitHub assignee is the "ball" and the Asana PR task mirrors it. Until the label is added, SGTM behaves as it always has: any approval or request for changes hands the PR back to the author. Once codeowner tasks are requested for a PR with codeowned files:

- **Changes requested** by anyone: to the author.
- **Approval**, when the *primary review* is in:
  - every codeowner requirement satisfied: to the author;
  - codeowner approvals still missing: to an outstanding subtask's assignee. Among outstanding subtasks SGTM prefers one whose assignee the author chose, then any with an assignee over one escalated to the author, then the one owning the fewest changed files, then the earliest created.
- **Approval by a codeowner before the primary review**: to a reviewer the author chose who has not reviewed yet, if there is one; otherwise unchanged.
- **Adding the label** moves the PR to a codeowner only if the primary review is already in.
- **Pushes and comments** change nothing, except that a codeowner SGTM assigned who was replaced on the subtask hands the PR to the replacement.

The *primary review* is an approval from anyone who is not a codeowner on this PR, or from a codeowner the author chose (asked to review, or set as GitHub assignee). Codeowners requested only by SGTM or by GitHub's automatic CODEOWNERS request count toward the codeowner side alone. SGTM only moves the PR while it is still assigned to whoever SGTM last assigned it to (the author included); a codeowner a person assigned the PR to by hand keeps it until they review.

The `persistent task assignee` label and follow-up review users keep their existing exemptions. **Review Status** becomes: Not Ready › Changes Requested › Approved (primary review in and every requirement satisfied) › Needs Codeowner Approval (primary review in) › Needs Review.

### Stacked pull requests

GitHub evaluates a PR in a GitHub-native stack against the stack's base, so SGTM reads `CODEOWNERS` from there and the heads-up comment says nothing special. For any other PR whose base is not the default branch (a Graphite or hand-managed stack) the heads-up comment warns that approvals are dismissed when the PR is rebased onto trunk, and suggests adding the label once the PR targets the default branch. The label is honored either way.

## Setup

1. **GitHub App permissions.** SGTM reads `CODEOWNERS` through the GraphQL API, which needs **Contents: Read** on the GitHub App (or a token with `repo` scope); without it the sync fails, is logged, and SGTM behaves as if the feature were off. Resolving team owners to people needs **Members: Read** on the organization; a team SGTM cannot see is logged and treated as empty. Creating the label needs **Issues: Write**; if SGTM cannot create it, the label can be created by hand and everything else still works. Requesting reviews, commenting and assigning use the **Pull requests: Write** permission SGTM already has. A comment SGTM cannot post or edit is logged and skipped; the subtasks and the PR task are still kept up to date.
2. **Codeowner project.** Create the shared project the subtasks are multi-homed into and note its ID:
   ```
   python3 scripts/setup_sgtm_tasks_project.py -p "<PAT>" create -n "Codeowner PR approval tasks" -t "<TEAM ID>" --codeowner-project
   ```
   Make sure the SGTM Asana user is a member of it.
3. **PR task projects.** Add the new fields to every "SGTM &lt;repo&gt; tasks" project (idempotent; existing fields are left alone and the "Needs Codeowner Approval" option is added to "Review Status"):
   ```
   python3 scripts/setup_sgtm_tasks_project.py -p "<PAT>" update -e "<EXISTING PROJECT ID>" --with-codeowner-fields
   ```
4. **Opt-in list (optional).** Create a JSON file in S3 for the heads-up comment, either a list of GitHub logins or `{"version": 1, "opted_in": {"<login>": {...}}}`. SGTM caches it for a minute. The Terraform module grants the Lambda read access to the path you configure.
5. **Terraform variables.**

   | Variable | Purpose |
   | --- | --- |
   | `TF_VAR_sgtm_feature__codeowner_tasks_enabled` | `true` to turn the feature on |
   | `TF_VAR_sgtm_feature__codeowner_tasks_project_id` | ID of the codeowner project from step 2 |
   | `TF_VAR_sgtm_feature__codeowner_tasks_opt_in_s3_path` | `bucket/key` of the opt-in list; empty for no heads-up comments |
   | `TF_VAR_sgtm_feature__codeowner_tasks_label` | the label (default `assign-tasks-to-codeowners`) |
   | `TF_VAR_sgtm_feature__codeowner_tasks_idle_business_days` | business days before an idle assignee is replaced (default `1`) |
   | `TF_VAR_sgtm_feature__codeowner_tasks_asana_workspace_id` | Asana workspace for out-of-office lookups; empty treats nobody as out of office |
   | `TF_VAR_sgtm_feature__codeowner_tasks_docs_url` | where "How it works" links point (default: this page on `master`) |
   | `TF_VAR_sgtm_feature__codeowner_tasks_org_docs_url` | optional link to your organization's CODEOWNERS docs |
   | `TF_VAR_sgtm_feature__codeowner_tasks_opt_in_command` | optional command shown for opting in, for example `z sgtm codeowner-tasks opt-in` |

## Operations

- **State.** SGTM keeps one JSON document per PR that touches codeowned files in the `sgtm-objects` table under the key `<PR node id>#codeowners`: when the label was seen, its own comment ids, the reviewers and assignees a person chose, the reviewers SGTM requested, the assignee SGTM last set, and one entry per subtask (task id, assignee, when created and assigned and why, status, files, hashes of what was last written). Every webhook is handled idempotently from a fresh GraphQL snapshot of the PR plus this state. If the state cannot be read, the PR task is updated as without the feature; if it cannot be written after a sync, that sync is reported as failed so the problem shows up in the logs rather than as a silently repeated action.
- **Caches.** Team membership and parsed `CODEOWNERS` are cached in the Lambda process for five minutes; the opt-in list for one minute; the label's existence per repository for the life of the process.
- **Failure mode.** Any error inside the codeowner sync is logged with a stack trace and the PR task is updated exactly as without the feature. A subtask is recorded in state the moment Asana creates it, and each subtask is maintained independently, so one broken subtask (deleted in Asana, say) neither stops the others nor gets duplicated on the next event.
- **Code.** `src/codeowners/`: `codeowners_file.py` (parser), `requirements.py` (owner sets and folding), `status.py` (evaluation and Review Status), `assignment.py` (subtask assignee choice, idleness), `pr_assignment.py` (PR assignee rules), `tasks.py` (subtask lifecycle), `texts.py` (every user-facing text), `state.py`, `context.py` (what the PR task's fields and description need), `controller.py` (wiring, called from `src/github/controller.py`). Team membership is fetched and cached through `src/github/logic.py`.
