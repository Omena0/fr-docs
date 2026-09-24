"""Shared utility functions for fr-docs."""


def normalized_site_prefix(config):
    prefix = str(config.get("site_path_prefix", "/")).strip()
    if not prefix:
        return "/"
    if not prefix.startswith("/"):
        prefix = "/" + prefix
    if not prefix.endswith("/"):
        prefix += "/"
    return prefix


def output_href(path, config):
    clean = str(path or "").lstrip("/")
    prefix = normalized_site_prefix(config)
    if not config.get("production", False):
        return clean
    if not prefix:
        return clean
    return prefix + clean


def output_site_prefix(config):
    return normalized_site_prefix(config) if config.get("production", False) else ""