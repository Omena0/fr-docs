"""Configuration accessor functions for fr-docs."""


def project_name(config):
    return config.get("project_name", "Project Name")


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


def feature_enabled(config, feature_name):
    value = features_config(config).get(feature_name, True)
    if isinstance(value, dict):
        return value.get("enabled", True)
    return bool(value)


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
