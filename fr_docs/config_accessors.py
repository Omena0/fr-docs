"""Configuration accessor functions for fr-docs."""

import warnings
from pathlib import Path


def project_name(config):
    return config.get("project_name", "Project Name")


def copyright_holder(config):
    if "_copyright_holder" in config:
        return config["_copyright_holder"]
    if configured := str(config.get("copyright_holder") or "").strip():
        config["_copyright_holder"] = configured
        return configured
    if config.get("_project_name_specified", "project_name" in config) and (
        name := str(config.get("project_name") or "").strip()
    ):
        config["_copyright_holder"] = name
        return name
    docs_path = Path(config.get("_docs_dir", ".")).resolve()
    holder = docs_path.parent.name or project_name(config)
    warnings.warn(
        "copyright_holder and project_name are not configured; "
        f"using docs folder parent name '{holder}'",
        stacklevel=2,
    )
    config["_copyright_holder"] = holder
    return holder


def site_prefix(config):
    prefix = str(config.get("site_path_prefix", "/")).strip()
    if not prefix:
        return "/"
    if not prefix.startswith("/"):
        prefix = f"/{prefix}"
    if not prefix.endswith("/"):
        prefix += "/"
    return prefix


def sidebar(config):
    return config.get("sidebar", [])


def build_settings(config):
    return config.get("build", {})


def versioning_config(config):
    return config.get("versioning", {})


def features_config(config):
    return config.get("features", {})


def custom_tags(config):
    """Return the custom-tag configuration as {tag_name: {label, display, class}}.

    Each entry maps an inline marker like ``[beta]`` to a badge. ``label``
    is the sidebar category name (sections whose name contains ``[beta]``
    are tagged), ``display`` is the badge text, and ``class`` is the CSS
    class used to style it.

    Accepts either a dict::

        "custom_tags": {"ext": {"label": "Extensions", "display": "ext"}}

    or a list of objects with a required ``tag`` field::

        "custom_tags": [{"tag": "ext", "label": "Extensions", "display": "ext"}]

    Defaults to a single ``ext`` tag for backwards compatibility.
    """
    raw = config.get("custom_tags")
    if raw is None:
        return {"ext": {"label": "Extensions", "display": "ext", "class": "ext-tag"}}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, list):
        result = {}
        for entry in raw:
            if not isinstance(entry, dict) or "tag" not in entry:
                continue
            tag = str(entry["tag"])
            result[tag] = {
                "label": str(entry.get("label", tag.capitalize())),
                "display": str(entry.get("display", tag)),
                "class": str(entry.get("class", "ext-tag")),
            }
        return result
    return {"ext": {"label": "Extensions", "display": "ext", "class": "ext-tag"}}


def feature_enabled(config, feature_name):
    # Default to False: features must be explicitly enabled in config.
    # Previously the default was True, which meant every feature was
    # on even when not configured — including features that should be
    # opt-in.
    value = features_config(config).get(feature_name, False)
    return value.get("enabled", False) if isinstance(value, dict) else bool(value)


def features_state(config):
    """Return a flat dict of every feature name to its enabled bool.

    Used to embed feature state into the page so client-side JS can
    gate behaviour (e.g. link previews) on the same decisions the
    builder made.
    """
    return {
        name: (
            (v.get("enabled", False) if isinstance(v, dict) else bool(v))
            if v is not None
            else False
        )
        for name, v in features_config(config).items()
    }


def header_links(config):
    """Return an ordered list of {name, href} links for the header nav.

    Defaults to a single "Docs" link back to the site root. Users can
    override with a dict mapping readable names to hrefs.
    """
    raw = config.get("header_links")
    if raw is None:
        return [{"name": "Docs", "href": "index.html"}]
    if isinstance(raw, dict):
        return [{"name": str(k), "href": str(v)} for k, v in raw.items()]
    if isinstance(raw, list):
        return [
            {"name": str(item.get("name", "")), "href": str(item.get("href", ""))}
            for item in raw
            if isinstance(item, dict)
        ]
    return [{"name": "Docs", "href": "index.html"}]


def footer_text(config):
    """Return the footer text. Defaults to the standard copyright line."""
    return str(config.get("footer_text", ""))


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
