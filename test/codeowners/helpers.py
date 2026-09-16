"""Shared fixtures for codeowner feature tests."""
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Set

from src.codeowners.codeowners_file import parse_codeowners
from src.codeowners.requirements import (
    OwnerSet,
    codeowned_files,
    requirements_for_files,
)
from src.codeowners.status import (
    CodeownerSummary,
    RequirementEvaluation,
    evaluate_requirement,
)
from src.github.models import PullRequest, ReviewState
from test.impl.builders import builder, build

SECDEV = "@Asana/secdev"
PLATFORM = "@Asana/platform"
CICD = "@Asana/cicd"
TEAM_MEMBERS: Dict[str, Set[str]] = {
    "Asana/secdev": {"jordan", "eli", "pete"},
    "Asana/platform": {"thelma", "vignir", "nicanor"},
    "Asana/cicd": {"dharmesh", "fangjian"},
}
ALL_MEMBERS: Set[str] = set().union(*TEAM_MEMBERS.values())

CODEOWNERS_TEXT = f"""
/lambda/auto_approver/ {SECDEV}
/modules/cell/ {PLATFORM} {SECDEV} {CICD}
/workflows/databricks_* @Asana/data
"""
AUTO_APPROVER = "lambda/auto_approver/config.yaml"
CELL_DATA = "modules/cell/data.tf"
CELL_LOCALS = "modules/cell/locals.tf"
DATABRICKS = "workflows/databricks_nightly.yml"

# GitHub login -> Asana gid used by the s3 mapping patch.
ASANA_GIDS: Dict[str, str] = {
    login: f"gid-{login}" for login in ALL_MEMBERS | {"author", "harshita", "outsider"}
}
ASANA_GIDS["dora"] = "gid-dora"  # data team member
TEAM_MEMBERS["Asana/data"] = {"dora"}


def resolve_pool(owner_set: OwnerSet) -> Set[str]:
    logins = set(owner_set.individual_logins())
    for slug in owner_set.team_slugs():
        logins |= TEAM_MEMBERS.get(slug, set())
    return logins


def gid_for(login: str):
    return ASANA_GIDS.get(login)


def login_for(gid: str):
    for login, candidate in ASANA_GIDS.items():
        if candidate == gid:
            return login
    return None


def at(hour: int, day: int = 14, month: int = 9) -> datetime:
    return datetime(2026, month, day, hour, 0, tzinfo=timezone.utc)


def review(login: str, state: ReviewState, when: datetime, commit: str = "abc12345"):
    return build(
        builder.review()
        .author(builder.user(login))
        .state(state)
        .submitted_at(when)
        .commit_oid(commit)
        .url(f"https://github.com/Asana/codez/pull/1#pullrequestreview-{login}")
    )


def pull_request(files: List[str], reviews=(), author: str = "author", **kwargs):
    pr_builder = (
        builder.pull_request()
        .author(builder.user(author))
        .number(436513)
        .title("Plumb permissionsCluster into cell Helm globals")
        .url("https://github.com/Asana/codez/pull/436513")
        .head_ref_oid("0fb846e3e7fc2aec8e017cc3f98ff77267009d28")
        .files(files)
        .reviews(list(reviews))
    )
    if kwargs.get("closed"):
        pr_builder = pr_builder.closed(True)
    if kwargs.get("merged"):
        pr_builder = pr_builder.merged(True).closed(True)
    return build(pr_builder)


def evaluations_for(pr: PullRequest) -> List[RequirementEvaluation]:
    rules = parse_codeowners(CODEOWNERS_TEXT)
    return [
        evaluate_requirement(
            requirement,
            resolve_pool,
            pr.reviews(),
            pr.author_handle(),
            merged=pr.merged(),
        )
        for requirement in requirements_for_files(rules, pr.changed_files())
    ]


def summary_for(
    pr: PullRequest, tasks_requested: bool = True, human_chosen: Iterable[str] = ()
) -> CodeownerSummary:
    rules = parse_codeowners(CODEOWNERS_TEXT)
    owned = codeowned_files(rules, pr.changed_files())
    evaluations = evaluations_for(pr)
    codeowner_logins: Set[str] = set()
    for owner_set in owned.values():
        codeowner_logins |= resolve_pool(owner_set)
    return CodeownerSummary(
        evaluations=evaluations,
        codeowned_files=owned,
        tasks_requested=tasks_requested,
        codeowner_logins=codeowner_logins,
        human_chosen_logins=set(human_chosen),
    )
