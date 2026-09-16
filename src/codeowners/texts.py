"""Every user-facing text the codeowner tasks feature writes.

Asana texts are Asana rich text (a restricted HTML subset inside ``<body>``);
GitHub texts are Markdown. Wording was reviewed on the design page before
implementation, so keep changes here deliberate.
"""
import hashlib
from datetime import date
from html import escape
from typing import Dict, Iterable, List, Optional, Sequence

import src.config as config
from src.asana.mentions import asana_mention_for_github_login, asana_task_link
from src.github.models import PullRequest, Review

from .requirements import OwnerSet
from .status import (
    CodeownerSummary,
    FileEvaluation,
    FileStatus,
    RequirementEvaluation,
    RequirementStatus,
)

# Hidden markers that let SGTM find and edit its own GitHub comments.
HEADS_UP_MARKER = "<!-- sgtm-codeowner-tasks-prompt -->"
CREATED_MARKER = "<!-- sgtm-codeowner-tasks-created -->"

LABEL_COLOR = "1d76db"


def label_description() -> str:
    return (
        "Ask SGTM to create an Asana review task for this PR's codeowners and "
        "route the PR to them once your primary reviewer approves."
    )


# --------------------------------------------------------------------------
# Links
# --------------------------------------------------------------------------


def team_url(team_slug: str) -> str:
    """`org/slug` -> the team's GitHub page."""
    org, slug = team_slug.split("/", 1)
    return f"https://github.com/orgs/{org}/teams/{slug}"


def diff_anchor(path: str) -> str:
    return "diff-" + hashlib.sha256(path.encode("utf-8")).hexdigest()


def owned_files_url(pr_url: str, viewer_login: str) -> str:
    """The PR's Changes view filtered to files the viewer owns (team membership
    counts; GitHub hides the filter when it would be a no-op)."""
    return f"{pr_url}/changes?owned-by%5B%5D={viewer_login}"


def file_diff_url(pr_url: str, path: str, viewer_login: Optional[str] = None) -> str:
    """Deep link that scrolls to `path`, with the ownership filter when a viewer
    login is known."""
    base = (
        owned_files_url(pr_url, viewer_login) if viewer_login else f"{pr_url}/changes"
    )
    return f"{base}#{diff_anchor(path)}"


def _a(href: str, text: str) -> str:
    return f'<a href="{escape(href)}">{escape(text)}</a>'


def _short_sha(sha: Optional[str]) -> str:
    return (sha or "")[:8]


# --------------------------------------------------------------------------
# Owner set rendering
# --------------------------------------------------------------------------


def owner_links_html(owner_set: OwnerSet) -> str:
    parts: List[str] = []
    for owner in owner_set.owners:
        if owner.startswith("@") and "/" in owner:
            slug = owner[1:]
            parts.append(_a(team_url(slug), slug.split("/", 1)[1]))
        elif owner.startswith("@"):
            parts.append(asana_mention_for_github_login(owner[1:]))
        else:
            parts.append(escape(owner))
    return " · ".join(parts)


def owner_links_markdown(owner_set: OwnerSet) -> str:
    parts: List[str] = []
    for owner in owner_set.owners:
        if owner.startswith("@") and "/" in owner:
            slug = owner[1:]
            parts.append(f"[{slug.split('/', 1)[1]}]({team_url(slug)})")
        elif owner.startswith("@"):
            login = owner[1:]
            # Linked, not @-mentioned, so nobody is notified by the comment itself.
            parts.append(f"[{login}](https://github.com/{login})")
        else:
            parts.append(owner)
    return " · ".join(parts)


# --------------------------------------------------------------------------
# Subtask
# --------------------------------------------------------------------------


def subtask_name(
    pull_request: PullRequest, owner_set: OwnerSet, several_sets: bool
) -> str:
    """`Codeowner review: #N - title`; the owner set is appended only when the
    PR needs several subtasks, so they can be told apart in lists."""
    suffix = f" ({owner_set.short_display()})" if several_sets else ""
    return (
        f"Codeowner review{suffix}: #{pull_request.number()} - {pull_request.title()}"
    )


def status_sentence(
    evaluation: RequirementEvaluation, pull_request: PullRequest
) -> str:
    head = _short_sha(pull_request.head_ref_oid())
    status = evaluation.status
    if status is RequirementStatus.APPROVED:
        review = evaluation.approval_review()
        if review is not None:
            return (
                f"Approved by {asana_mention_for_github_login(review.author_handle())}"
                f" on {_short_sha(review.commit_oid()) or head}."
            )
        return "Approved."
    if status is RequirementStatus.APPROVAL_STALE:
        review = evaluation.stale_review()
        who = (
            asana_mention_for_github_login(review.author_handle())
            if review is not None
            else "A codeowner"
        )
        return (
            f"{who}'s approval was dismissed by push {head}; a fresh approval on the"
            " latest commit is needed."
        )
    if status is RequirementStatus.CHANGES_REQUESTED:
        review = evaluation.changes_requested_review()
        who = (
            asana_mention_for_github_login(review.author_handle())
            if review is not None
            else "A codeowner"
        )
        return f"Changes requested by {who}. The PR task is back with the author."
    if status is RequirementStatus.NO_LONGER_REQUIRED:
        return "The latest push no longer changes any file owned by these codeowners."
    if status is RequirementStatus.MERGED_WITH_BYPASS:
        return (
            "The PR merged without a codeowner approval. Nothing is required: close"
            " this task, or use it as a reminder to review the merged change."
        )
    return f"No codeowner has approved the latest commit ({head})."


def file_status_text(file_evaluation: FileEvaluation) -> str:
    review = file_evaluation.review
    who = asana_mention_for_github_login(review.author_handle()) if review else ""
    if file_evaluation.status is FileStatus.APPROVED:
        return f"approved by {who}"
    if file_evaluation.status is FileStatus.STALE:
        return f"approval from {who} dismissed by a push"
    if file_evaluation.status is FileStatus.CHANGES_REQUESTED:
        return f"changes requested by {who}"
    return "needs approval"


def footer_html(prefix: str) -> str:
    parts = [f"ℹ️ {prefix}"]
    if config.SGTM_FEATURE__CODEOWNER_TASKS_OPT_IN_COMMAND:
        parts.append(
            "Enroll with <code>"
            + escape(config.SGTM_FEATURE__CODEOWNER_TASKS_OPT_IN_COMMAND)
            + "</code>"
        )
    parts.append(_a(config.SGTM_FEATURE__CODEOWNER_TASKS_DOCS_URL, "How it works"))
    if config.SGTM_FEATURE__CODEOWNER_TASKS_ORG_DOCS_URL:
        parts.append(
            _a(config.SGTM_FEATURE__CODEOWNER_TASKS_ORG_DOCS_URL, "CODEOWNERS docs")
        )
    return " · ".join(parts)


def subtask_description(
    pull_request: PullRequest,
    evaluation: RequirementEvaluation,
    parent_task_id: str,
    assignee_login: Optional[str],
    assignment_reason: str,
) -> str:
    pr_url = pull_request.url()
    requirement = evaluation.requirement
    owner_set = requirement.owner_set
    total_files = len(pull_request.changed_files())
    files = evaluation.files

    lines: List[str] = [
        "<em>This is a one-way sync from GitHub to Asana. Do not edit this task or"
        " comment on it!</em>",
        "",
        f"🔗 {_a(pr_url, pr_url)}",
        "🧵 PR task: "
        + asana_task_link(
            parent_task_id, f"#{pull_request.number()} - {pull_request.title()}"
        ),
        f"🛡️ Codeowners: {owner_links_html(owner_set)} (any member can approve)",
        f"✍️ PR author: {asana_mention_for_github_login(pull_request.author_handle())}",
        "",
        f"❗️Codeowner approval: <strong>{escape(evaluation.status.value)}</strong>. "
        + status_sentence(evaluation, pull_request),
    ]
    if assignee_login:
        lines.append(
            f"👤 Assigned to {asana_mention_for_github_login(assignee_login)},"
            f" {escape(assignment_reason)}."
        )
    elif assignment_reason:
        lines.append(f"👤 {escape(assignment_reason)}")

    lines += [
        "",
        f"<strong>Codeowned files changed in this PR ({len(files)} of {total_files}):</strong>",
    ]
    items: List[str] = []
    for file_evaluation in files:
        item = (
            _a(
                file_diff_url(pr_url, file_evaluation.path, assignee_login),
                file_evaluation.path,
            )
            + " — "
            + file_status_text(file_evaluation)
        )
        if file_evaluation.owners != owner_set:
            item += f" (also owned by {owner_links_html(file_evaluation.owners)})"
        items.append(f"<li>{item}</li>")
    lines.append("<ul>" + "".join(items) + "</ul>")
    if requirement.covered_files:
        lines.append(
            'Files marked "also owned by" can be approved by any of their owners;'
            " an approval from this task's codeowners covers them too."
        )
    if assignee_login:
        url = owned_files_url(pr_url, assignee_login)
        lines.append(
            f"🔎 Only the files you own, as {escape(assignee_login)} sees them: {_a(url, url)}"
        )
    lines += [
        f"📂 All {total_files} changed files: {_a(pr_url + '/files', pr_url + '/files')}",
        "",
        "<strong>To complete this task</strong>, approve the PR on GitHub on its latest"
        " commit. SGTM marks it complete when a valid codeowner approval is in place,"
        " reopens it if a later push dismisses that approval, and closes it when the"
        " PR merges or is closed.",
        "",
        footer_html("Created by SGTM's opt-in codeowner tasks feature."),
    ]
    return "<body>" + "\n".join(lines) + "</body>"


# --------------------------------------------------------------------------
# Subtask comments (Asana rich text)
# --------------------------------------------------------------------------


def _body(text: str) -> str:
    return f"<body>{text}</body>"


def comment_reassigned_out_of_office(
    new_login: str, old_login: str, until: Optional[date]
) -> str:
    when = f" until {until.strftime('%b %-d')}" if until and until != date.max else ""
    return _body(
        f"Reassigned to {asana_mention_for_github_login(new_login)}:"
        f" {asana_mention_for_github_login(old_login)} is out of office in Asana{when}."
    )


def comment_reassigned_idle(new_login: str, business_days: int) -> str:
    unit = "business day" if business_days == 1 else "business days"
    return _body(
        f"Reassigned to {asana_mention_for_github_login(new_login)} after"
        f" {business_days} {unit} without a review. Any codeowner can still approve."
    )


def comment_reassigned_to_requested(new_login: str) -> str:
    return _body(
        f"Reassigned to {asana_mention_for_github_login(new_login)}, who was requested"
        " as a reviewer on this PR."
    )


def comment_assigned_after_escalation(new_login: str, reason: str) -> str:
    return _body(
        f"Assigned to {asana_mention_for_github_login(new_login)}, {escape(reason)}."
    )


def comment_escalated(author_login: str) -> str:
    return _body(
        "No available codeowner: everyone is the PR author or out of office."
        f" Assigned to the PR author {asana_mention_for_github_login(author_login)}"
        " to find a reviewer."
    )


def comment_approved(review: Review, owner_set: OwnerSet) -> str:
    return _body(
        f"Approved by {asana_mention_for_github_login(review.author_handle())} on commit"
        f" {_short_sha(review.commit_oid())}: {_a(review.url(), 'review')}. Marking this"
        " task complete. It reopens if a later push dismisses the approval."
    )


def comment_approved_after_merge(review: Review) -> str:
    return _body(
        f"Approved after merge by {asana_mention_for_github_login(review.author_handle())}:"
        f" {_a(review.url(), 'review')}. Marking this task complete."
    )


def comment_approval_dismissed(
    reviewer_login: Optional[str], push_sha: Optional[str]
) -> str:
    who = (
        asana_mention_for_github_login(reviewer_login)
        if reviewer_login
        else "a codeowner"
    )
    return _body(
        f"Reopening: the approval from {who} was dismissed by a new push"
        f" ({_short_sha(push_sha)}). A fresh approval on the latest commit is needed."
    )


def comment_changes_requested(review: Review, assignee_login: Optional[str]) -> str:
    holder = (
        f" this task stays with {asana_mention_for_github_login(assignee_login)}"
        if assignee_login
        else " this task stays open"
    )
    return _body(
        f"{asana_mention_for_github_login(review.author_handle())} requested changes:"
        f" {_a(review.url(), 'review')}. The PR task is back with the author;{holder}"
        " until a codeowner approves the updated PR."
    )


def _file_list(paths: Iterable[str]) -> str:
    return "<ul>" + "".join(f"<li>{escape(p)}</li>" for p in paths) + "</ul>"


def comment_no_longer_required(dropped_files: Sequence[str]) -> str:
    return _body(
        "Completing: the latest push no longer changes any file owned by these"
        f" codeowners. Dropped from the diff:{_file_list(dropped_files)}This task"
        " reopens if the PR changes such files again."
    )


def comment_required_again(files: Sequence[str]) -> str:
    return _body(
        "Reopening: the PR again changes files owned by these codeowners:"
        + _file_list(files)
    )


def comment_merged_with_bypass(merged_by_login: Optional[str]) -> str:
    who = (
        f" by {asana_mention_for_github_login(merged_by_login)}"
        if merged_by_login
        else ""
    )
    return _body(
        f"PR merged{who} without a codeowner approval, presumably through a ruleset"
        " bypass. Nothing is required here: close this task, or use it as a reminder"
        " to review the merged change. SGTM will complete it if a codeowner approves"
        " the merged PR."
    )


def comment_closed_unmerged() -> str:
    return _body("PR closed without merging. Closing.")


# --------------------------------------------------------------------------
# PR task (parent)
# --------------------------------------------------------------------------

_GLYPHS = {
    RequirementStatus.NEEDED: "⬜",
    RequirementStatus.APPROVED: "✅",
    RequirementStatus.APPROVAL_STALE: "⚠️",
    RequirementStatus.CHANGES_REQUESTED: "❌",
    RequirementStatus.NO_LONGER_REQUIRED: "➖",
    RequirementStatus.MERGED_WITH_BYPASS: "🔶",
}


def parent_not_requested_block(codeowned_files: Dict[str, OwnerSet], label: str) -> str:
    owner_sets = sorted({owner_set for owner_set in codeowned_files.values()})
    sets_text = "; ".join(owner_links_html(owner_set) for owner_set in owner_sets)
    count = len(codeowned_files)
    noun = "file is" if count == 1 else "files are"
    return (
        "🛡️ <strong>Codeowner reviews: not yet requested.</strong>"
        f" {count} {noun} owned by {sets_text}. Add the <code>{escape(label)}</code>"
        " label on GitHub when ready for codeowners to review."
    )


def parent_checklist_block(
    summary: CodeownerSummary,
    assignees_by_owner_key: Dict[str, Optional[str]],
    subtask_ids_by_owner_key: Dict[str, str],
) -> str:
    active = [
        e
        for e in summary.evaluations
        if e.status is not RequirementStatus.NO_LONGER_REQUIRED
    ]
    approved = sum(1 for e in active if e.status is RequirementStatus.APPROVED)
    items: List[str] = []
    for evaluation in summary.evaluations:
        key = evaluation.owner_set.key()
        parts = [
            f"{_GLYPHS[evaluation.status]} {owner_links_html(evaluation.owner_set)}",
            _checklist_status_text(evaluation),
        ]
        assignee = assignees_by_owner_key.get(key)
        if assignee and evaluation.is_outstanding():
            parts.append(f"assigned to {asana_mention_for_github_login(assignee)}")
        if key in subtask_ids_by_owner_key:
            parts.append(asana_task_link(subtask_ids_by_owner_key[key], "subtask"))
        items.append("<li>" + " · ".join(parts) + "</li>")
    return (
        f"🛡️ <strong>Codeowner reviews: {approved} of {len(active)} approved</strong>"
        + "<ul>"
        + "".join(items)
        + "</ul>"
    )


def _checklist_status_text(evaluation: RequirementEvaluation) -> str:
    status = evaluation.status
    if status is RequirementStatus.APPROVED:
        review = evaluation.approval_review()
        if review is not None:
            return (
                f"approved by {asana_mention_for_github_login(review.author_handle())}"
                f" on {_short_sha(review.commit_oid())}"
            )
        return "approved"
    if status is RequirementStatus.APPROVAL_STALE:
        review = evaluation.stale_review()
        who = (
            asana_mention_for_github_login(review.author_handle())
            if review
            else "a codeowner"
        )
        return f"approval stale, was {who}"
    if status is RequirementStatus.CHANGES_REQUESTED:
        review = evaluation.changes_requested_review()
        who = (
            asana_mention_for_github_login(review.author_handle())
            if review
            else "a codeowner"
        )
        return f"changes requested by {who}"
    if status is RequirementStatus.NO_LONGER_REQUIRED:
        return "no longer required"
    if status is RequirementStatus.MERGED_WITH_BYPASS:
        return "merged with bypass, informational"
    return "needed"


def parent_footer() -> str:
    return footer_html(
        "Codeowner tracking on this task comes from SGTM's opt-in codeowner tasks feature."
    )


def parent_all_approved_comment(summary: CodeownerSummary) -> str:
    sets = "; ".join(owner_links_html(e.owner_set) for e in summary.evaluations)
    approvers = sorted(
        {
            review.author_handle()
            for e in summary.evaluations
            for review in [e.approval_review()]
            if review is not None
        }
    )
    by = (
        ", approved by "
        + " and ".join(asana_mention_for_github_login(login) for login in approvers)
        if approvers
        else ""
    )
    return _body(f"🛡️ All codeowner approvals are in place ({sets}{by}).")


# --------------------------------------------------------------------------
# GitHub comments (Markdown)
# --------------------------------------------------------------------------


def _docs_line_markdown() -> str:
    links = [f"[SGTM codeowner tasks]({config.SGTM_FEATURE__CODEOWNER_TASKS_DOCS_URL})"]
    if config.SGTM_FEATURE__CODEOWNER_TASKS_ORG_DOCS_URL:
        links.append(
            f"[CODEOWNERS docs]({config.SGTM_FEATURE__CODEOWNER_TASKS_ORG_DOCS_URL})"
        )
    return "Docs: " + " · ".join(links)


def _opt_in_phrase() -> str:
    command = config.SGTM_FEATURE__CODEOWNER_TASKS_OPT_IN_COMMAND
    return f" with `{command}`" if command else ""


def heads_up_comment(
    codeowned_files: Dict[str, OwnerSet],
    requirement_count: int,
    label: str,
    base_ref_name: str,
    default_branch: Optional[str],
    in_native_stack: bool,
) -> str:
    count = len(codeowned_files)
    noun = "file that has" if count == 1 else "files that have"
    lines = [
        HEADS_UP_MARKER,
        f"**Codeowner review required.** This PR changes {count} {noun} designated code"
        " owners. Each file needs an approval from one of its owners, on the latest"
        " commit, before it can merge.",
        "",
        "| File | Codeowners (any one can approve) |",
        "|---|---|",
    ]
    for path, owner_set in sorted(codeowned_files.items()):
        lines.append(f"| `{path}` | {owner_links_markdown(owner_set)} |")
    lines.append("")
    if default_branch and base_ref_name != default_branch and not in_native_stack:
        lines += [
            f"**This PR targets `{base_ref_name}`, not trunk.** On a Graphite or"
            " hand-managed stack, approvals here are dismissed when the PR below merges"
            " and this one is rebased onto trunk, so consider adding the label only once"
            f" this PR targets `{default_branch}`. GitHub-native stacks are evaluated"
            " against the stack base and can be labeled right away.",
            "",
        ]
    plural = "" if requirement_count == 1 else "s"
    lines += [
        f"**When you're done iterating and ready for codeowners**, add the `{label}`"
        " label. SGTM will then:",
        "",
        f"- create one Asana subtask per group of codeowners under this PR's Asana task"
        f" ({requirement_count} here), assign it to an available codeowner, and request"
        " their review here on GitHub;",
        "- move this PR's Asana task to that codeowner once your primary reviewer has"
        " approved, and back to you when anyone requests changes;",
        f"- complete the subtask{plural} when the approval is in place, and close"
        f" {'it' if not plural else 'them'} when the PR merges.",
        "",
        "Prefer a specific codeowner? Request their review here on GitHub, or reassign"
        " the Asana subtask to them once it exists. SGTM follows your choice and will"
        " not re-pick unless that person is out of office.",
        "",
        "Codeowners must approve your **latest** push: a new commit dismisses earlier"
        " approvals. Adding the label after your last round of changes saves everyone"
        " a re-review.",
        "",
        f"<sub>{_docs_line_markdown()} · You're seeing this because you opted in"
        f"{_opt_in_phrase()}.</sub>",
    ]
    return "\n".join(lines)


def created_block_markdown(
    assignees: Dict[str, Optional[str]],
    subtask_urls: Dict[str, str],
    owner_sets: Dict[str, OwnerSet],
    reasons: Dict[str, str],
) -> str:
    """The block appended to the heads-up comment once the label is added."""
    lines = [
        "",
        "---",
        "",
        f"**✅ Codeowner review task{'s' if len(owner_sets) != 1 else ''} created.**",
    ]
    for key, owner_set in owner_sets.items():
        assignee = assignees.get(key)
        who = (
            f"assigned to [{assignee}](https://github.com/{assignee}), {reasons.get(key, '')}"
            if assignee
            else "no codeowner available, assigned to the author"
        )
        link = f" · [Asana]({subtask_urls[key]})" if key in subtask_urls else ""
        lines.append(f"- {owner_links_markdown(owner_set)}: {who}{link}")
    lines += [
        "",
        "Review requested on GitHub. Prefer someone else? Request their review here or"
        " reassign the subtask; SGTM follows your choice.",
    ]
    return "\n".join(lines)


def label_added_comment(
    label: str,
    codeowned_files: Dict[str, OwnerSet],
    assignees: Dict[str, Optional[str]],
    subtask_urls: Dict[str, str],
    owner_sets: Dict[str, OwnerSet],
    reasons: Dict[str, str],
) -> str:
    """Posted for authors who did not get the heads-up comment (not opted in)."""
    count = len(codeowned_files)
    all_sets = sorted({owner_set for owner_set in codeowned_files.values()})
    owners_text = " and ".join(owner_links_markdown(s) for s in all_sets)
    lines = [
        CREATED_MARKER,
        f"**`{label}` label added.** This SGTM feature creates Asana tasks for the"
        " codeowner reviews a PR needs and routes them automatically.",
        "",
        f"**✅ Task{'s' if len(owner_sets) != 1 else ''} created.** This PR changes"
        f" {count} {'file' if count == 1 else 'files'} owned by {owners_text}; one"
        " approval from any owner of a file satisfies GitHub for it.",
    ]
    for key, owner_set in owner_sets.items():
        assignee = assignees.get(key)
        who = (
            f"assigned to [{assignee}](https://github.com/{assignee}), {reasons.get(key, '')}"
            if assignee
            else "no codeowner available, assigned to the author"
        )
        link = f" · [Asana]({subtask_urls[key]})" if key in subtask_urls else ""
        lines.append(f"- {owner_links_markdown(owner_set)}: {who}{link}")
    lines += [
        "",
        "Review requested on GitHub. Prefer someone else? Request their review here or"
        " reassign the subtask; SGTM follows your choice.",
        "",
        "SGTM will move this PR's Asana task to the codeowner once your primary reviewer"
        " has approved, back to you when anyone requests changes, and complete the"
        " subtask when the codeowner approval is in place. Codeowners must approve your"
        " **latest** push; a new commit dismisses earlier approvals.",
        "",
        "<sub>Want a heads-up like this as soon as a PR of yours touches codeowned"
        f" files, before you add the label? Opt in{_opt_in_phrase()}."
        f" {_docs_line_markdown()}.</sub>",
    ]
    return "\n".join(lines)
