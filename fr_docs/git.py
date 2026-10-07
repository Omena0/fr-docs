"""Git metadata collection and processing for fr-docs."""

import html
import json
import os
import re
import subprocess
from contextlib import suppress
from pathlib import Path

from .config_accessors import git_meta_filename, live_label, out_dir, src_dir
from .slug import slug_page_key


def _parse_commit_log(log_out):
    """Parse git log output into commits and versions."""
    commits = []
    versions = []
    for line in log_out.splitlines():
        if not line:
            continue

        parts = line.split("\x01", 1)

        if len(parts) == 2:
            h, msg = parts
        else:
            h = parts[0]
            msg = ""

        commits.append(h)
        if m := re.match(r"^\s*([0-9]+[A-Za-z])\s*[-:—–]\s*(.+)", msg):
            code = m[1].upper()
            label = m[2].strip()
            versions.append({"code": code, "commit": h, "label": label})

    return commits, versions


def _build_pages_by_commit(out, slugs):
    """Build pages_by_commit mapping from git log output.

    Each slug in ``slugs`` is a normalized slug like ``core/entity``. The
    git log ``--name-only`` output lists file paths like
    ``docs/src/core/entity.md``; we strip the configured source prefix
    and ``.md`` suffix to recover the slug.
    """
    pages_by_commit = {}
    current_commit = None
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue

        if re.fullmatch(r"[0-9a-f]{7,40}", line):
            current_commit = line
        elif current_commit:
            # Recover the slug from the file path: strip dir prefix and .md
            slug = line
            if slug.endswith(".md"):
                slug = slug[:-3]
            # Try to match against known slugs (handles prefix variations)
            matched = None
            for s in slugs:
                src_path = s + ".md"
                if line.endswith(src_path) or line.endswith(f"/{src_path}") or line == src_path:
                    matched = s
                    break
            if matched is None:
                # Fall back to basename matching for flat layouts
                base = Path(line).stem
                for s in slugs:
                    if s.rsplit("/", 1)[-1] == base:
                        matched = s
                        break
            if matched is not None:
                pages_by_commit.setdefault(current_commit, []).append(matched)
    return pages_by_commit


def _build_slug_last_commits(slugs, config, repo_root):
    """Build slug_last_commit mapping for each slug."""
    slug_last_commit = {}
    for slug in slugs:
        src = src_map_path(config).replace("{slug}", slug)
        out = subprocess.check_output(
            ["git", "log", "-1", "--pretty=format:%H", "--", src],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

        if out and re.fullmatch(r"[0-9a-f]{7,40}", out):
            slug_last_commit[slug] = out
    return slug_last_commit


def collect_git_metadata(config):
    """Collect git metadata including repo info, commits, and versions."""
    git_meta = {
        "repo": None,
        "commits": [],
        "tags": {},
        "versions": [],
        "src_map": {},
        "pages_by_commit": {},
        "slug_last_commit": {},
        "site_path": str(out_dir(config)),
        "src_path": src_map_path(config).replace("{slug}", ""),
    }

    repo_root = Path(config["_docs_dir"]).parent

    remote_url = subprocess.check_output(
        ["git", "remote", "get-url", "origin"],
        cwd=repo_root,
        text=True,
    ).strip()

    if m := re.search(r"github.com[:/](.+?)(?:\.git)?$", remote_url):
        git_meta["repo"] = m[1]

    log_out = subprocess.check_output(
        ["git", "log", "--pretty=format:%H\x01%s", "--reverse"],
        cwd=repo_root,
        text=True,
    )

    commits, versions = _parse_commit_log(log_out)
    git_meta["commits"] = commits
    git_meta["versions"] = versions

    slugs = list(config.get("_slug_page_keys", {}).keys())
    for slug in slugs:
        git_meta["src_map"][slug_page_key(slug, config)] = src_map_path(config).replace(
            "{slug}", slug
        )

    # Populate pages_by_commit: which slugs exist at each commit.
    # Used by the client to filter the sidebar when viewing a
    # historical version.
    if not slugs:
        return git_meta

    out = subprocess.check_output(
        [
            "git",
            "log",
            "--pretty=format:%H",
            "--name-only",
            "--",
        ]
        + [src_map_path(config).replace("{slug}", s) for s in slugs],
        cwd=repo_root,
        text=True,
        stderr=subprocess.DEVNULL,
    )

    git_meta["pages_by_commit"] = _build_pages_by_commit(out, slugs)
    git_meta["slug_last_commit"] = _build_slug_last_commits(slugs, config, repo_root)

    return git_meta


def src_map_path(config) -> str:
    """Return the source markdown path relative to the repo root.

    e.g. ``docs/src/{slug}.md``. The client uses this to fetch
    historical markdown from ``raw.githubusercontent.com``.\n
        :param config: Configuration dictionary
        :type config: dict
        :return: Source path pattern
        :rtype: str
    """
    docs_dir = Path(config.get("_docs_dir", "."))
    repo_root = docs_dir.parent
    rel = Path(os.path.relpath(docs_dir / src_dir(config), repo_root))
    return f"{rel}/{{slug}}.md"


def write_git_metadata(git_meta, config) -> None:
    """Write git metadata to disk."""
    with suppress(OSError, TypeError):
        Path(config["_out_dir"], git_meta_filename(config)).write_text(
            json.dumps(git_meta, separators=(",", ":")), encoding="utf-8"
        )


def build_version_options(git_meta, config):
    """Pre-render version selector HTML options.\n
        :param git_meta: Git metadata dictionary
        :type git_meta: dict
        :param config: Configuration dictionary
        :type config: dict
        :return: HTML options string
        :rtype: str
    """

    try:
        opts = [f'<option value="">{live_label(config)}</option>']
        if git_meta["versions"]:
            for v in reversed(git_meta["versions"]):
                code = v.get("code")
                commit = v.get("commit", "")
                label = v.get("label", "")
                if not code:
                    continue
                esc_code = html.escape(code)
                if label:
                    esc_label = html.escape(label)
                    esc_commit = html.escape(commit[:8])
                    opts.append(
                        f'<option value="{esc_code}" data-label="{esc_label}" data-commit="{esc_commit}">'
                        f"  {esc_code}"
                        f"</option>"
                    )
                else:
                    esc_commit = html.escape(commit[:8])
                    opts.append(
                        f'<option value="{esc_code}" data-commit="{esc_commit}">'
                        f"  {esc_code}"
                        f"</option>"
                    )
        elif git_meta["commits"]:
            latest = git_meta["commits"][-1]
            esc_commit = html.escape(latest[:8])
            opts.append(
                f'<option value="{latest}" data-commit="{esc_commit}">'
                f"  {esc_commit}"
                f"</option>"
            )

        config["_version_options"] = "\n".join(opts)
    except KeyError, TypeError, AttributeError:
        config["_version_options"] = f'<option value="">{live_label(config)}</option>'

    return config["_version_options"]
