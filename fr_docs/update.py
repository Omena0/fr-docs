"""Update fr-docs resources (script.js, style.css, fonts) from the repo."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

from .config import load_config
from .config_accessors import out_dir, project_name, src_dir as config_src_dir
from .build import (
    _resolve_script_version,
    _write_script_js,
    _minify_static_asset,
    _script_version_hash,
)


def _fetch_remote(repo_root, rel_path):
    """Fetch a file from the fr-docs repo via git show HEAD:path."""
    try:
        return subprocess.check_output(
            ["git", "show", f"HEAD:{rel_path}"],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="replace")
    except (subprocess.CalledProcessError, OSError):
        return None


def _git_current_commit(repo_root):
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="replace").strip()
    except (subprocess.CalledProcessError, OSError):
        return None


def _git_remote_url(repo_root):
    try:
        return subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="replace").strip()
    except (subprocess.CalledProcessError, OSError):
        return None


def _is_fr_docs_repo(repo_root):
    """Return True if the repo is the fr-docs repo itself."""
    url = _git_remote_url(repo_root) or ""
    return "Omena0/fr-docs" in url or "omena0/fr-docs" in url.lower()


def update_resources(config):
    """Update script.js, style.css, favicon.svg, and fonts from the fr-docs repo.

    Only runs when the current repo is not the fr-docs repo (so we can read
    the source files from git). For downstream repos, the resources are
    pulled from PyPI via the `fr-docs` package or copied from the docs/
    directory.
    """
    docs_path = Path(config["_docs_dir"]).resolve()
    repo_root = docs_path.parent
    if _is_fr_docs_repo(repo_root):
        print("   In the fr-docs repo; skipping remote resource update.")
        return

    resources = ["script.js", "style.css", "favicon.svg"]
    updated = []
    for name in resources:
        rel = f"docs/{name}"
        remote = _fetch_remote(repo_root, rel)
        if remote is None:
            continue

        local_path = docs_path / name
        if name == "script.js":
            version, content = _resolve_script_version(repo_root, rel, local_path)
            _write_script_js(local_path, version, content)
            updated.append(f"{name} (v{version})")
        else:
            local_path.write_text(remote, encoding="utf-8")
            updated.append(name)

    # Update fonts
    fonts_dir = docs_path / "fonts"
    if fonts_dir.is_dir():
        remote_fonts = _fetch_remote(repo_root, "docs/fonts")
        # Can't fetch a directory; instead list remote files via git ls-tree
        try:
            out = subprocess.check_output(
                ["git", "ls-tree", "-r", "--name-only", "HEAD", "docs/fonts"],
                cwd=repo_root,
                stderr=subprocess.DEVNULL,
            ).decode("utf-8", errors="replace")
            for line in out.splitlines():
                fname = Path(line).name
                content = _fetch_remote(repo_root, line)
                if content is not None:
                    (fonts_dir / fname).write_text(content, encoding="utf-8")
                    updated.append(f"fonts/{fname}")
        except (subprocess.CalledProcessError, OSError):
            pass

    if updated:
        print(f"   Updated: {', '.join(updated)}")
    else:
        print("   No resources updated.")


def main(argv=None) -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="fr-docs update",
        description="Update fr-docs resources (script.js, style.css, fonts) from the repo.",
    )
    parser.add_argument(
        "--config",
        help="Path to the configuration JSON file.",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    print(f"🔄 Updating {project_name(config)} resources...")
    update_resources(config)
    print("✅ Update complete.")


if __name__ == "__main__":
    main()