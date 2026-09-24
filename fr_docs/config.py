#!/usr/bin/env python3
"""Configuration loading for the fr-docs documentation builder."""

import json
from pathlib import Path

DEFAULT_CONFIG = {
    "project_name": "Project Name",
    "project_url": "",
    "site_path_prefix": "/",
    "src_dir": "src",
    "out_dir": "site",
    "docs_dir": ".",
    "sidebar": [],
    "build": {
        "workers": 18,
        "minify_html": True,
        "optimize_html": True,
        "zstd_level": 22,
        "search_index_filename": "search_index.zst",
        "git_meta_filename": "git_meta.json",
    },
    "versioning": {
        "commit_message_pattern": r"^\s*([0-9]+[A-Za-z])\s*[-:—–]\s*(.+)",
        "live_label": "Live",
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
    """Load and validate the documentation builder configuration."""
    if config_path is None:
        config_path = Path.cwd() / "config.json"
        if not config_path.exists():
            docs_config = Path.cwd() / "docs" / "config.json"
            if docs_config.exists():
                config_path = docs_config
    else:
        config_path = Path(config_path)

    config = DEFAULT_CONFIG
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        config = _merge(DEFAULT_CONFIG, loaded)

    config_path = config_path.resolve()
    docs_dir = (
        Path(config["docs_dir"]).resolve() if config["docs_dir"] else config_path.parent
    )
    src_dir = docs_dir / config["src_dir"] if config["src_dir"] else docs_dir / "src"
    out_dir = docs_dir / config["out_dir"] if config["out_dir"] else docs_dir / "site"

    config["_config_path"] = str(config_path)
    config["_docs_dir"] = str(docs_dir)
    config["_src_dir"] = str(src_dir)
    config["_out_dir"] = str(out_dir)

    return config
