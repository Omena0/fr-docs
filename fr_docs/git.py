"""Git metadata collection and processing for fr-docs."""

import html
import json
import os
import re
import subprocess
from pathlib import Path

from .config_accessors import git_meta_filename, live_label, out_dir, src_dir
from .slug import slug_page_key


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

    m = re.search(r"github.com[:/](.+?)(?:\.git)?$", remote_url)
    if m:
        git_meta["repo"] = m[1]

    log_out = subprocess.check_output(
        ["git", "log", "--pretty=format:%H%x01%s", "--reverse"],
        cwd=repo_root,
        text=True,
    )

    for line in log_out.splitlines():
        if not line:
            continue

        parts = line.split("\x01", 1)

        if len(parts) == 2:
            h, msg = parts

        else:
            h = parts[0]
            msg = ""

        git_meta["commits"].append(h)
        m = re.match(r"^\s*([0-9]+[A-Za-z])\s*[-:—–]\s*(.+)", msg)

        if m:
            code = m.group(1).upper()
            label = m.group(2).strip()
            git_meta["versions"].append(
                {"code": code, "commit": h, "label": label}
            )

    slugs = list(config.get("_slug_page_keys", {}).keys())
    for slug in slugs:
        git_meta["src_map"][slug_page_key(slug, config)] = (
            src_map_path(config).replace("{slug}", slug)
        )

    # Populate pages_by_commit: which slugs exist at each commit.
    # Used by the client to filter the sidebar when viewing a
    # historical version.
    if not slugs:
        return git_meta

    out = subprocess.check_output(
        [
            "git", "log", "--pretty=format:%H",
            "--name-only", "--",
        ]
        + [src_map_path(config).replace("{slug}", s) for s in slugs],
        cwd=repo_root,
        text=True,
        stderr=subprocess.DEVNULL,
    )

    current_commit = None
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue

        if re.fullmatch(r"[0-9a-f]{7,40}", line):
            current_commit = line

        elif current_commit:
            # line is a source path like "src/index.md"
            slug = Path(line).stem
            if slug in slugs:
                git_meta["pages_by_commit"].setdefault(
                    current_commit, []
                ).append(slug)

    # Also record which commit each slug was last modified at, so the
    # client can fall back to a single-commit lookup.
    for slug in slugs:
        src = src_map_path(config).replace("{slug}", slug)
        out = subprocess.check_output(
            ["git", "log", "-1", "--pretty=format:%H", "--", src],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

        if out and re.fullmatch(r"[0-9a-f]{7,40}", out):
            git_meta.setdefault("slug_last_commit", {})[slug] = out

    return git_meta


def src_map_path(config) -> str:
    """Return the source markdown path relative to the repo root.

    e.g. ``docs/src/{slug}.md``. The client uses this to fetch
    historical markdown from ``raw.githubusercontent.com``.
    """
    docs_dir = Path(config.get("_docs_dir", "."))
    repo_root = docs_dir.parent
    rel = os.path.relpath(docs_dir / src_dir(config), repo_root)
    return f"{rel}/{{slug}}.md"


def write_git_metadata(git_meta, config) -> None:
    """Write git metadata to disk."""
    try:
        with open(
            os.path.join(config["_out_dir"], git_meta_filename(config)),
            "w",
            encoding="utf-8",
        ) as gf:
            json.dump(git_meta, gf, separators=(",", ":"))
    except OSError, TypeError:
        pass


def build_version_options(git_meta, config):
    """Pre-render version selector HTML options."""

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
                        f'  {esc_code}'
                        f'</option>'
                    )
                else:
                    esc_commit = html.escape(commit[:8])
                    opts.append(
                        f'<option value="{esc_code}" data-commit="{esc_commit}">'
                        f'  {esc_code}'
                        f'</option>'
                    )
        elif git_meta["commits"]:
            latest = git_meta["commits"][-1]
            esc_commit = html.escape(latest[:8])
            opts.append(
                f'<option value="{latest}" data-commit="{esc_commit}">'
                f'  {esc_commit}'
                f'</option>'
            )

        config["_version_options"] = "\n".join(opts)
    except KeyError, TypeError, AttributeError:
        config["_version_options"] = f'<option value="">{live_label(config)}</option>'

    return config["_version_options"]
