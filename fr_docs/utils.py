"""Shared utility functions for fr-docs."""


def normalized_site_prefix(config):
    prefix = str(config.get("site_path_prefix", "/")).strip()
    if not prefix:
        return "/"
    if not prefix.startswith("/"):
        prefix = f"/{prefix}"
    if not prefix.endswith("/"):
        prefix += "/"
    return prefix


def output_href(path, config):
    clean = str(path or "").lstrip("/")
    prefix = normalized_site_prefix(config)
    if not config.get("production", False):
        return clean
    return prefix + clean if prefix else clean


def output_site_prefix(config: dict) -> str:
    return normalized_site_prefix(config) if config.get("production", False) else "/"


def output_asset_href(path, config):
    """Return a root-relative href for a static asset.

    Static assets (CSS, JS, favicon, fonts) must resolve from any page
    depth, so they always use a root-relative path (e.g. ``/style.css``).
    """
    clean = str(path or "").lstrip("/")
    prefix = normalized_site_prefix(config)
    return prefix + clean if prefix else "/" + clean
