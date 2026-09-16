"""Group a pull request's changed files into the codeowner approvals it needs.

GitHub requires, for every codeowned file, one approval from any owner listed on
that file's winning CODEOWNERS line. SGTM creates one subtask per distinct
*owner set* (the owners on that line), so a PR touching several files that share
the same owners gets one subtask, and files owned by several teams at once ask
for one approval rather than one per team.

Folding: when one owner set is a strict superset of another owner set present on
the same PR, an approval for the smaller set also satisfies the larger set's
files (every owner of the smaller set is an owner of the larger one), so the
larger set's files are folded into the smaller set's subtask instead of getting
a subtask of their own.
"""
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .codeowners_file import (
    CodeownersRule,
    is_individual_owner,
    is_team_owner,
    owners_of,
)

TEAM_SLUG_SUFFIX_TO_STRIP = "-workday-sync"


@dataclass(frozen=True, order=True)
class OwnerSet:
    """The owners listed on one CODEOWNERS line, as a sorted tuple of raw tokens."""

    owners: Tuple[str, ...]

    @classmethod
    def of(cls, owners: Sequence[str]) -> "OwnerSet":
        return cls(tuple(sorted(set(owners))))

    def key(self) -> str:
        """Stable identifier, used in DynamoDB keys: ``Asana/a-team+Asana/b-team``."""
        return "+".join(owner.lstrip("@") for owner in self.owners)

    def team_slugs(self) -> List[str]:
        """``org/team`` for every team owner."""
        return [owner[1:] for owner in self.owners if is_team_owner(owner)]

    def individual_logins(self) -> List[str]:
        return [owner[1:] for owner in self.owners if is_individual_owner(owner)]

    def display_names(self) -> List[str]:
        """Human-readable owner names: team slug without the org, or ``@login``."""
        names: List[str] = []
        for owner in self.owners:
            if is_team_owner(owner):
                names.append(owner.split("/", 1)[1])
            else:
                names.append(owner)
        return names

    def display(self) -> str:
        return " + ".join(self.display_names())

    def short_display(self) -> str:
        """Display with the common team-slug suffix removed, for task titles."""
        return " + ".join(
            name[: -len(TEAM_SLUG_SUFFIX_TO_STRIP)]
            if name.endswith(TEAM_SLUG_SUFFIX_TO_STRIP)
            else name
            for name in self.display_names()
        )

    def is_strict_superset_of(self, other: "OwnerSet") -> bool:
        return set(self.owners) > set(other.owners)


@dataclass
class CodeownerRequirement:
    """One subtask's worth of codeowner approval.

    ``files`` are owned exactly by ``owner_set``. ``covered_files`` are owned by
    a strict superset of it and were folded in; the value is that file's own
    owner set, so descriptions can say who else may approve it.
    """

    owner_set: OwnerSet
    files: List[str] = field(default_factory=list)
    covered_files: Dict[str, OwnerSet] = field(default_factory=dict)

    def all_files(self) -> List[str]:
        return sorted(self.files + list(self.covered_files))

    def owners_for_file(self, path: str) -> OwnerSet:
        return self.covered_files.get(path, self.owner_set)


def codeowned_files(
    rules: Sequence[CodeownersRule], files: Sequence[str]
) -> Dict[str, OwnerSet]:
    """Map every codeowned changed file to its owner set. Unowned files are omitted."""
    result: Dict[str, OwnerSet] = {}
    for path in files:
        owners = owners_of(rules, path)
        if owners:
            result[path] = OwnerSet.of(owners)
    return result


def requirements_for_files(
    rules: Sequence[CodeownersRule], files: Sequence[str]
) -> List[CodeownerRequirement]:
    """Group changed files into owner sets and fold supersets into subsets.

    Returns requirements sorted by owner-set key, each with sorted file lists.
    """
    by_owner_set: Dict[OwnerSet, CodeownerRequirement] = {}
    for path, owner_set in codeowned_files(rules, files).items():
        requirement = by_owner_set.setdefault(
            owner_set, CodeownerRequirement(owner_set=owner_set)
        )
        requirement.files.append(path)

    folded: Dict[OwnerSet, CodeownerRequirement] = {}
    for owner_set, requirement in by_owner_set.items():
        target = _smallest_strict_subset(owner_set, by_owner_set.keys())
        if target is None:
            folded.setdefault(owner_set, CodeownerRequirement(owner_set=owner_set))
            folded[owner_set].files.extend(requirement.files)
        else:
            folded.setdefault(target, CodeownerRequirement(owner_set=target))
            for path in requirement.files:
                folded[target].covered_files[path] = owner_set

    result = sorted(folded.values(), key=lambda r: r.owner_set.key())
    for requirement in result:
        requirement.files.sort()
    return result


def _smallest_strict_subset(
    owner_set: OwnerSet, candidates: Iterable[OwnerSet]
) -> Optional[OwnerSet]:
    subsets = [
        candidate
        for candidate in candidates
        if owner_set.is_strict_superset_of(candidate)
    ]
    if not subsets:
        return None
    # Fewest owners first, then a stable tie-break on the key.
    return min(subsets, key=lambda s: (len(s.owners), s.key()))
