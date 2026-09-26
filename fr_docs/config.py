#!/usr/bin/env python3
"""Configuration loading for the fr-docs documentation builder."""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_CONFIG = {
    "$schema": "https://raw.githubusercontent.com/Omena0/fr-docs/main/config.schema.json",
    "project_name": "Project Name",
    "copyright_holder": "CHANGE_ME",
    "project_url": "",
    "site_path_prefix": "/",
    "src_dir": "src",
    "out_dir": "site",
    "docs_dir": ".",
    "source_files": {
        "search_dirs": ["parent", "src_parent", "docs"],
        "patterns": ["docs/src/*.md", "docs/*.js", "docs/*.css"],
        "ignore_dirs": [],
    },
    "sidebar": [],
    "build": {
        "workers": 18,
        "minify_html": True,
        "optimize_html": True,
        "zstd_level": 22,
        "search_index_filename": "search_index.zst",
        "git_meta_filename": "git_meta.zst",
    },
    "versioning": {
        "commit_message_pattern": r"^\s*([0-9]+[A-Za-z])\s*[-:—–]\s*(.+)",
        "live_label": "Live",
    },
    "features": {
        "backlinks": True,
        "related": True,
        "auto_link": True,
        "versioning": True,
        "search": True,
        "code_references": True,
        "link_preview": True,
        "code_highlighting": True,
        "blockquotes": True,
        "ext_tags": True,
        "inline_copy": True,
    },
}


def _merge(base, override):
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_path=None):
    """Load and validate the documentation builder configuration.\n
    :param config_path: Optional path to config file
    :type config_path: str | Path | None
    """
    if config_path is None:
        config_path = Path.cwd() / "config.json"
        if not config_path.exists():
            docs_config = Path.cwd() / "docs" / "config.json"
            if docs_config.exists():
                config_path = docs_config
    else:
        config_path = Path(config_path)

    config = DEFAULT_CONFIG
    project_name_specified = False
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            loaded = json.load(f)
        config = _merge(DEFAULT_CONFIG, loaded)
        project_name_specified = "project_name" in loaded

    config_path = config_path.resolve()
    if docs_dir_raw := config["docs_dir"]:
        docs_dir_path = Path(docs_dir_raw)
        docs_dir = (
            docs_dir_path
            if docs_dir_path.is_absolute()
            else (config_path.parent / docs_dir_path).resolve()
        )

    else:
        docs_dir = config_path.parent

    src_dir = docs_dir / config["src_dir"] if config["src_dir"] else docs_dir / "src"

    out_dir_raw = (
        config.get("build", {}).get("out_dir") or config.get("out_dir") or "site"
    )
    out_dir = (
        Path(out_dir_raw) if Path(out_dir_raw).is_absolute() else docs_dir / out_dir_raw
    )

    config["_project_name_specified"] = project_name_specified
    config["_config_path"] = str(config_path)
    config["_docs_dir"] = str(docs_dir)
    config["_src_dir"] = str(src_dir)
    config["_out_dir"] = str(out_dir)

    return config
