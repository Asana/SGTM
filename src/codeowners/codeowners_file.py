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
  ``**`` matches across directories. Negation and ``[...]`` ranges are not
  supported by GitHub and not supported here. A backslash escapes the next
  character, so ``docs/my\ file.md`` names a path with a space.
* A ``#`` preceded by whitespace starts a comment.
* A line with a pattern but no owners clears ownership for matching paths.
* A line whose owners are not all ``@login``, ``@org/team`` or an email address
  is skipped, as GitHub skips lines with invalid syntax.

Owner tokens are kept as written (``@org/team``, ``@login`` or an email address).
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


# Owner syntax GitHub accepts: a user, a team, or an email address.
_LOGIN = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
_OWNER_RE = re.compile(
    rf"^@{_LOGIN}(?:/[A-Za-z0-9_.-]+)?$|^[^@\s/]+@[^@\s/]+\.[^@\s/]+$"
)


def is_valid_owner(owner: str) -> bool:
    return _OWNER_RE.match(owner) is not None


def _tokenize(line: str) -> List[str]:
    """Split a CODEOWNERS line on whitespace, honouring backslash escapes and
    stopping at a ``#`` that starts a token (an inline comment)."""
    tokens: List[str] = []
    current: List[str] = []
    escaped = False
    for char in line:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char.isspace():
            if current:
                tokens.append("".join(current))
                current = []
        elif char == "#" and not current:
            break
        else:
            current.append(char)
    if current:
        tokens.append("".join(current))
    return tokens


_NEVER_MATCHES = re.compile(r"(?!)")


def compile_pattern(raw_pattern: str) -> "re.Pattern[str]":
    pattern = raw_pattern.strip()
    if pattern == "/":
        # A bare slash names the root directory itself, which no file is.
        return _NEVER_MATCHES
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
        parts = _tokenize(raw)
        if not parts:
            continue
        pattern, owners = parts[0], tuple(parts[1:])
        if not all(is_valid_owner(owner) for owner in owners):
            # GitHub skips lines with invalid syntax rather than guessing.
            continue
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
    for rule in reversed(rules):
        if rule.matches(path):
            return rule
    return None


def owners_of(rules: Sequence[CodeownersRule], path: str) -> Tuple[str, ...]:
    """The owner tokens for ``path``, or an empty tuple when nobody owns it."""
    rule = owning_rule(rules, path)
    return rule.owners if rule is not None else ()
