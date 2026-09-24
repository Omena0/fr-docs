"""Git metadata collection and processing for fr-docs."""

import html
import json
import os
import re
import subprocess
from pathlib import Path

from .config_accessors import git_meta_filename, live_label, src_dir
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
    }

    try:
        repo_root = Path(config["_docs_dir"]).parent

        try:
            remote_url = subprocess.check_output(
                ["git", "remote", "get-url", "origin"],
                cwd=repo_root,
                text=True,
            ).strip()
        except (FileNotFoundError, subprocess.CalledProcessError):
            remote_url = ""

        m = re.search(r"github.com[:/](.+?)(?:\.git)?$", remote_url)
        if m:
            m.group(1)

        try:
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
                m = re.match(
                    r"^\s*([0-9]+[A-Za-z])\s*[-:—–]\s*(.+)", msg
                )
                if m:
                    code = m.group(1).upper()
                    label = m.group(2).strip()
                    git_meta["versions"].append(
                        {"code": code, "commit": h, "label": label}
                    )
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

        slugs = list(config.get("_slug_page_keys", {}).keys())
        for slug in slugs:
            git_meta["src_map"][slug_page_key(slug, config)] = src_map_path(config)

    except (FileNotFoundError, subprocess.CalledProcessError, OSError) as e:
        pass

    return git_meta


def src_map_path(config):
    """Return the source markdown path pattern used in git metadata."""
    return f"{src_dir(config)}/{{slug}}.md"


def write_git_metadata(git_meta, config):
    """Write git metadata to disk."""
    try:
        with open(
            os.path.join(config["_out_dir"], git_meta_filename(config)),
            "w",
            encoding="utf-8",
        ) as gf:
            json.dump(git_meta, gf, separators=(",", ":"))
    except (OSError, TypeError) as e:
        pass


def build_version_options(git_meta, config):
    """Pre-render version selector HTML options."""
    from .config_accessors import live_label

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
                        f'<option value="{esc_code}" data-label="{esc_label}" data-commit="{esc_commit}">{esc_code}</option>'
                    )
                else:
                    esc_commit = html.escape(commit[:8])
                    opts.append(
                        f'<option value="{esc_code}" data-commit="{esc_commit}">{esc_code}</option>'
                    )
        else:
            if git_meta["commits"]:
                latest = git_meta["commits"][-1]
                esc_commit = html.escape(latest[:8])
                opts.append(
                    f'<option value="{latest}" data-commit="{esc_commit}">{esc_commit}</option>'
                )

        config["_version_options"] = "\n".join(opts)
    except (KeyError, TypeError, AttributeError):
        config["_version_options"] = f'<option value="">{live_label(config)}</option>'

    return config["_version_options"]