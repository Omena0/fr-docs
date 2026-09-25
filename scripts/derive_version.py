#!/usr/bin/env python3
"""Derive the PEP 440 version for the PyPI publish workflow.

Version codes look like ``2A``: a major number followed by a letter that
encodes the minor version (A=1, B=2, C=3, ...). This script converts that
code into a PEP 440 version string and prints ``key=value`` lines suitable
for ``$GITHUB_OUTPUT``.

- On ``push`` the code is read from the most recent commit whose subject
  starts with a version code (walking back through history); if none exists
  the publish is skipped.
- On ``workflow_dispatch`` the same commit-derived code is used, but the
  publish always runs (falling back to ``0.1.0`` when no version code exists
  in history).

In both cases the patch is bumped past the highest patch already published on
PyPI for that major.minor, so a re-run can never collide with an existing
distribution.

If PyPI is unreachable the publish proceeds with patch 0.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.error
import urllib.request

CODE_RE = re.compile(r"^(\d+)([A-Za-z])\b")
PYPI_URL = "https://pypi.org/pypi/fr-docs/json"


def log(message: str) -> None:
    print(message, file=sys.stderr)


def letter_to_minor(letter: str) -> int:
    """Convert a letter to its minor version number (A=1, B=2, ...)."""
    return ord(letter.lower()) - ord("a") + 1


def latest_versioned_commit_subject(event: str) -> str | None:
    """Most recent commit whose subject starts with a version code.

    On ``push`` only the HEAD commit is inspected, so a release is published
    solely when the pushed commit itself starts with a version prefix (a
    non-versioned follow-up commit no longer triggers a publish). On
    ``workflow_dispatch`` (manual) history is walked back so the last version
    code can be bumped into a fresh patch release.
    """
    args = (
        ["git", "log", "-1", "--pretty=%s"]
        if event == "push"
        else ["git", "log", "--pretty=%s"]
    )
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=True,
    )
    return next((
            line.strip()
            for line in result.stdout.splitlines()
            if CODE_RE.match(line.strip())),
        None,
    )


def published_patches(major: str, minor: str) -> set[int]:
    """Return the set of patch numbers already published for major.minor."""
    try:
        with urllib.request.urlopen(PYPI_URL, timeout=15) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        log(f"warning: could not query PyPI ({exc}); publishing with patch 0")
        return set()
    patches: set[int] = set()
    prefix = f"{major}.{minor}."
    for version in data.get("releases", {}):
        if not version.startswith(prefix):
            continue
        rest = version[len(prefix) :]
        if rest.isdigit():
            patches.add(int(rest))
    return patches


def next_patch(major: str, minor: str, base: int) -> int:
    """Smallest patch >= base not already published on PyPI."""
    existing = published_patches(major, minor)
    patch = base
    while patch in existing:
        patch += 1
    return patch


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else ""

    subject = latest_versioned_commit_subject(event)
    if subject is None:
        if event == "workflow_dispatch":
            # No version code anywhere in history: start at 0.1.0
            print("version=0.1.0")
            print("release_title=0A")
            print("should_publish=true")
            return 0
        print("should_publish=false")
        log("Skipping publish — no version prefix in commit history")
        return 0

    match = CODE_RE.match(subject)
    assert match is not None
    code = match.group(0)
    major, minor_letter = match.groups()
    minor = letter_to_minor(minor_letter)
    patch = next_patch(major, minor, base=0)
    version = f"{major}.{minor}.{patch}"
    release_title = code if patch == 0 else f"{code}{patch}"

    print(f"version={version}")
    print(f"release_title={release_title}")
    print("should_publish=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
