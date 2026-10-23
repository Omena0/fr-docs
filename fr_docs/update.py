"""Update fr-docs resources (script.js, style.css, fonts) from upstream."""

import tempfile
from pathlib import Path

from .build import (
    _git_script_versions,
    _script_version_hash,
    _write_script_js,
)
from .config import load_config
from .config_accessors import project_name
from .init import (
    FAVICON_SVG_URL,
    SCRIPT_JS_URL,
    STYLE_CSS_URL,
    download_file,
    run_fetch_fonts,
)


def _script_update_needed(local_path, remote_version):
    """Return True if local script.js should be updated to the given version.

    Mirrors the version logic:
    - If local has no version but matches a known historical blob, adopt that version.
    - Update if the local version is missing or lower than the latest (remote_version).
    - Never update if the latest version is identical to the local version (no-op).
    """
    local_version, local_hash = _script_version_hash(local_path)
    effective_local_version = local_version

    if local_version == 0:
        docs_dir = local_path.parent.parent
        script_rel = str(local_path.relative_to(docs_dir)) + "/script.js"
        hist = _git_script_versions(docs_dir, script_rel)
        for ver, h in hist:
            if h == local_hash and ver > 0:
                effective_local_version = ver
                break

    return remote_version > effective_local_version


def update_resources(config):
    """Update script.js, style.css, favicon.svg, and fonts from the fr-docs upstream repo.

    Downloads the latest resources from raw.githubusercontent.com and writes them
    to the local docs/ directory. For script.js, preserves version numbering
    by reading the version from the downloaded content.
    """
    docs_path = Path(config["_docs_dir"]).resolve()
    updated = []

    # Update script.js
    local_script = docs_path / "script.js"
    if local_script.exists():
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".js", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            if download_file(SCRIPT_JS_URL, tmp_path):
                remote_version, _ = _script_version_hash(tmp_path)
                if _script_update_needed(local_script, remote_version):
                    content = tmp_path.read_text(encoding="utf-8")
                    _write_script_js(local_script, remote_version, content)
                    updated.append(f"script.js (v{remote_version})")
        finally:
            tmp_path.unlink(missing_ok=True)

    # Update style.css
    local_style = docs_path / "style.css"
    if download_file(STYLE_CSS_URL, local_style):
        updated.append("style.css")

    # Update favicon.svg
    local_favicon = docs_path / "favicon.svg"
    if download_file(FAVICON_SVG_URL, local_favicon):
        updated.append("favicon.svg")

    # Update fonts (download from Google Fonts, generate fonts.css)
    fonts_dir = docs_path / "fonts"
    if fonts_dir.is_dir():
        old_count = len(list(fonts_dir.iterdir()))
        result = run_fetch_fonts(docs_path)
        if result == 0:
            new_count = len(list(fonts_dir.iterdir()))
            if new_count > old_count:
                updated.append(f"fonts ({new_count - old_count} new)")
            else:
                updated.append("fonts (refreshed)")

    if updated:
        print(f"   Updated: {', '.join(updated)}")
    else:
        print("   No resources updated.")


def main(argv=None) -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="fr-docs update",
        description="Update fr-docs resources (script.js, style.css, fonts) from upstream.",
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