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


def canonical_url(slug, config):
    """Return the canonical URL for a page slug with a trailing slash.

    Used for sitemaps and ``<link rel="canonical">``. Each URL ends with
    a trailing slash so it matches the canonical URL served by static
    hosting (e.g. GitHub Pages rewrites ``/fr-os`` to ``/fr-os/``, and a
    sitemap URL without the trailing slash would trigger a redirect —
    which Google rejects).

    The ``site_url`` config value should be the full base URL including any
    path prefix (e.g. ``https://example.com/docs/``).
    """
    site_url = str(config.get("site_url", "")).strip()
    if not site_url:
        return ""
    if not site_url.endswith("/"):
        site_url += "/"

    clean = str(slug or "").lstrip("/")
    if clean in ("", "index"):
        return site_url
    return site_url + clean + "/"
