"""Codeowner review tasks.

SGTM can create one Asana subtask per group of codeowners whose approval a pull
request needs, route the PR's task between codeowners and the primary reviewer,
and keep everything in sync with GitHub. See docs/codeowner_tasks.md.

This package is layered:

* ``codeowners_file``: parse a CODEOWNERS file and find the owners of a path.
* ``requirements``: group a PR's changed files into owner sets, one per subtask.
"""
