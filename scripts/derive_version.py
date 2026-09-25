#!/usr/bin/env python3
"""Derive the PEP 440 version for the PyPI publish workflow.

Version codes look like ``2A``: a major number followed by a letter that
encodes the minor version (A=1, B=2, C=3, ...). This script converts that
code into a PEP 440 version string and prints ``key=value`` lines suitable
for ``$GITHUB_OUTPUT``.

- On ``push`` the code is read from the latest commit message.
- On ``workflow_dispatch`` the code is taken from the most recent tag and
  the patch number is bumped.
"""
from __future__ import annotations

import re
import subprocess
import sys

CODE_RE = re.compile(r"^(\d+)([A-Za-z])")


def log(message: str) -> None:
    print(message, file=sys.stderr)


def letter_to_minor(letter: str) -> int:
    """Convert a letter to its minor version number (A=1, B=2, ...)."""
    return ord(letter.lower()) - ord("a") + 1


def code_to_semver(code: str, patch: int) -> str:
    match = CODE_RE.match(code)
    if not match:
        raise ValueError(f"invalid version code: {code!r}")
    major, minor_letter = match.groups()
    return f"{major}.{letter_to_minor(minor_letter)}.{patch}"


def head_commit_subject() -> str:
    return subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def latest_tag() -> str | None:
    result = subprocess.run(
        ["git", "tag", "--list", "[0-9]*[A-Za-z]*", "--sort=-creatordate"],
        capture_output=True,
        text=True,
        check=True,
    )
    for line in result.stdout.splitlines():
        line = line.strip()
        if CODE_RE.match(line):
            return line
    return None


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else ""

    if event == "workflow_dispatch":
        tag = latest_tag()
        if tag is None:
            # No previous release: start at 0.1.0
            print("version=0.1.0")
            print("release_title=0A")
            print("should_publish=true")
            return 0
        version = code_to_semver(tag, patch=1)
        release_title = f"{tag}1"
    else:
        subject = head_commit_subject()
        match = CODE_RE.match(subject)
        if match is None:
            print("should_publish=false")
            log("Skipping publish — no version prefix in commit message")
            return 0
        code = match.group(0)
        version = code_to_semver(code, patch=0)
        release_title = code

    print(f"version={version}")
    print(f"release_title={release_title}")
    print("should_publish=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())