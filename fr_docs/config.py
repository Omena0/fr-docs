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


def project_name(config):
    return config.get("project_name", "Project Name")


def site_prefix(config):
    prefix = str(config.get("site_path_prefix", "/")).strip()
    if not prefix:
        return "/"
    if not prefix.startswith("/"):
        prefix = "/" + prefix
    if not prefix.endswith("/"):
        prefix += "/"
    return prefix


def sidebar(config):
    return config.get("sidebar", [])


def build_settings(config):
    return config.get("build", {})


def versioning_config(config):
    return config.get("versioning", {})


def src_dir(config):
    return config.get("_src_dir", "src")


def out_dir(config):
    return config.get("_out_dir", "site")


def docs_dir(config):
    return config.get("_docs_dir", ".")


def search_index_filename(config):
    return build_settings(config).get("search_index_filename", "search_index.zst")


def git_meta_filename(config):
    return build_settings(config).get("git_meta_filename", "git_meta.json")


def zstd_level(config):
    return build_settings(config).get("zstd_level", 22)


def workers(config):
    return build_settings(config).get("workers", 18)


def minify_html(config):
    return build_settings(config).get("minify_html", True)


def optimize_html(config):
    return build_settings(config).get("optimize_html", True)


def commit_message_pattern(config):
    return versioning_config(config).get(
        "commit_message_pattern", r"^\s*([0-9]+[A-Za-z])\s*[-:—–]\s*(.+)"
    )


def live_label(config):
    return versioning_config(config).get("live_label", "Live")


def project_url(config):
    return config.get("project_url", "")


def src_map_path(config):
    """Return the source markdown path pattern used in git metadata."""
    return f"{src_dir(config)}/{{slug}}.md"


def is_project_root():
    return Path.cwd().name == "fr-docs"
