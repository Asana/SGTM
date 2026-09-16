"""CODEOWNERS parser and matcher implementing GitHub's semantics.

Rules, from
https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners:

* Lines are ``pattern owner owner ...``; ``#`` starts a comment; blank lines are
  ignored.
* The LAST matching pattern wins for a given path.
* A pattern with no slash (other than a trailing one) matches at any depth.
* A pattern containing a slash is anchored to the repository root; the leading
  ``/`` is optional.
* A trailing ``/`` restricts the match to a directory and everything under it.
* A pattern that names a directory also matches everything under it (gitignore
  behaviour), so ``**/logs`` owns every file in any ``logs`` directory. A pattern
  whose last segment contains a wildcard does not: ``docs/*`` matches
  ``docs/a.md`` but not ``docs/sub/b.md``.
* ``*`` matches anything except ``/``; ``?`` matches one non-slash character;
  ``**`` matches across directories. Negation, escaping and ``[...]`` ranges are
  not supported by GitHub and not supported here.
* A line with a pattern but no owners clears ownership for matching paths.

Owner tokens are kept verbatim (``@org/team``, ``@login`` or an email address).
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

# Where GitHub looks for the file, in the order it searches.
CODEOWNERS_PATHS: Tuple[str, ...] = (
    ".github/CODEOWNERS",
    "CODEOWNERS",
    "docs/CODEOWNERS",
)


@dataclass(frozen=True)
class CodeownersRule:
    pattern: str
    owners: Tuple[str, ...]
    line_number: int
    regex: "re.Pattern[str]" = field(repr=False, compare=False)

    def matches(self, path: str) -> bool:
        return self.regex.match(path.lstrip("/")) is not None

    def team_slugs(self) -> List[str]:
        """Owners of the form ``@org/team``, returned as ``org/team``."""
        return [owner[1:] for owner in self.owners if is_team_owner(owner)]

    def individual_logins(self) -> List[str]:
        """Owners of the form ``@login``, returned as ``login``."""
        return [owner[1:] for owner in self.owners if is_individual_owner(owner)]


def is_team_owner(owner: str) -> bool:
    return owner.startswith("@") and "/" in owner


def is_individual_owner(owner: str) -> bool:
    return owner.startswith("@") and "/" not in owner


def _glob_to_regex(pattern: str) -> str:
    """Translate a CODEOWNERS glob, already stripped of leading and trailing
    slashes, into a regex fragment matching a full repository-relative path."""
    out: List[str] = []
    i = 0
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == "*":
            if pattern.startswith("**/", i):
                # zero or more leading directories
                out.append("(?:.*/)?")
                i += 3
                continue
            if pattern.startswith("**", i):
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(c))
        i += 1
    return "".join(out)


def compile_pattern(raw_pattern: str) -> "re.Pattern[str]":
    pattern = raw_pattern.strip()
    dir_only = pattern.endswith("/")
    pattern = pattern.rstrip("/")
    anchored = pattern.startswith("/") or "/" in pattern
    pattern = pattern.lstrip("/")

    if pattern in ("", "*", "**"):
        return re.compile(r"^.*$")

    body = _glob_to_regex(pattern)
    prefix = "^" if anchored else r"^(?:.*/)?"
    last_segment = pattern.rsplit("/", 1)[-1]
    last_segment_has_wildcard = any(ch in last_segment for ch in "*?")
    if dir_only:
        # `/build/logs/`, `apps/`: the directory and everything beneath it, never
        # a plain file with that name.
        suffix = r"(?:/.*)$"
    elif last_segment_has_wildcard:
        # `*.js`, `docs/*`, `databricks_*`: a file glob, no "everything beneath".
        suffix = "$"
    else:
        # `**/logs`, `/apps/github`, `/CODEOWNERS`: a literal name; if it names a
        # directory, everything beneath it is owned too.
        suffix = r"(?:/.*)?$"
    return re.compile(prefix + body + suffix)


def parse_codeowners(text: str) -> List[CodeownersRule]:
    rules: List[CodeownersRule] = []
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # GitHub treats `#` as the start of an inline comment when preceded by
        # whitespace.
        if " #" in line:
            line = line.split(" #", 1)[0].rstrip()
        parts = line.split()
        pattern, owners = parts[0], tuple(parts[1:])
        rules.append(
            CodeownersRule(
                pattern=pattern,
                owners=owners,
                line_number=line_number,
                regex=compile_pattern(pattern),
            )
        )
    return rules


def owning_rule(rules: Sequence[CodeownersRule], path: str) -> Optional[CodeownersRule]:
    """Return the last rule matching ``path``, or None.

    A matching rule with no owners still wins and yields no owners, exactly like
    GitHub.
    """
    winner: Optional[CodeownersRule] = None
    for rule in rules:
        if rule.matches(path):
            winner = rule
    return winner


def owners_of(rules: Sequence[CodeownersRule], path: str) -> Tuple[str, ...]:
    """The owner tokens for ``path``, or an empty tuple when nobody owns it."""
    rule = owning_rule(rules, path)
    return rule.owners if rule is not None else ()
