"""Slug normalization and output-key utilities for fr-docs."""


def slug_basename(slug):
    """Extract the filename part from a possibly prefixed slug (e.g. 'core/entity' → 'entity')."""
    normalized = str(slug).replace("\\", "/").strip("/")
    return normalized.rsplit("/", 1)[-1] if normalized else ""


def normalize_slug(slug):
    """Normalize slugs to forward-slash format for cross-platform consistency.
    Also resolves relative path segments like '..' and '.'.
    """
    # Convert to forward slashes and strip
    normalized = str(slug).replace("\\", "/").strip("/")
    # Resolve relative path segments
    parts = []
    for part in normalized.split("/"):
        if part == "..":
            if parts:
                parts.pop()
        elif part and part != ".":
            parts.append(part)
    return "/".join(parts)


def build_slug_page_keys(slugs):
    """Build a mapping of normalized slug → normalized slug (identity mapping).

    With directory-tree output, file name collisions are avoided by
    preserving the directory structure in the output path, so no
    disambiguation suffixes are needed.
    """
    return {normalize_slug(slug): normalize_slug(slug) for slug in slugs}


def slug_page_key(slug, config):
    """Return the stable output key for a slug (the normalized slug)."""
    return normalize_slug(slug)


def slug_output_name(slug, config=None) -> str:
    """Return output HTML filename for a slug, preserving directory structure.

    Slugs like 'core/entity' produce 'core/entity.html'. The 'index' slug
    at the root produces 'index.html'; an 'index' nested under a directory
    (e.g. 'core/index') produces 'core/index.html'.
    """
    if config is None:
        return f"{slug}.html"
    return f"{normalize_slug(slug)}.html"


def relative_slug_path(from_slug, to_slug):
    """Compute the page-relative path from ``from_slug`` to ``to_slug``.

    Returns a string like ``../index.html`` or ``core/entity.html`` suitable
    for use as an ``href`` value in a page at ``from_slug``.
    """
    from_name = slug_output_name(from_slug)
    to_name = slug_output_name(to_slug)

    from_parts = from_name.split("/")
    to_parts = to_name.split("/")

    # Find common prefix
    i = 0
    while i < min(len(from_parts), len(to_parts)) and from_parts[i] == to_parts[i]:
        i += 1

    # Number of directory levels to go up (from the from_page's directory)
    # from_parts has the filename as the last element; we need to go up
    # from the directory containing from_name.
    up = len(from_parts) - 1 - i
    # Remaining path to the target
    down = to_parts[i:]

    parts = [".."] * up + down
    return "/".join(parts) if parts else to_name