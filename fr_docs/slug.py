"""Slug normalization and output-key utilities for fr-docs."""


def slug_basename(slug):
    """Extract the filename part from a possibly prefixed slug (e.g. 'core/entity' → 'entity')."""
    normalized = str(slug).replace("\\", "/").strip("/")
    return normalized.rsplit("/", 1)[-1] if normalized else ""


def normalize_slug(slug):
    """Normalize slugs to forward-slash format for cross-platform consistency."""
    return str(slug).replace("\\", "/").strip("/")


def build_slug_page_keys(slugs):
    """Build unique output keys for slugs, disambiguating basename collisions."""
    groups = {}
    for slug in slugs:
        norm = normalize_slug(slug)
        base = slug_basename(norm).lower()
        groups.setdefault(base, []).append(norm)

    keys = {}
    used = set()
    for base, entries in sorted(groups.items()):
        entries = sorted(set(entries))
        has_collision = len(entries) > 1
        for norm in entries:
            if not has_collision:
                base_key = slug_basename(norm)
            elif base == "index" and norm == "index":
                base_key = "index"
            else:
                base_key = norm.replace("/", "__")

            candidate = base_key
            suffix = 2
            while candidate in used:
                candidate = f"{base_key}-{suffix}"
                suffix += 1

            used.add(candidate)
            keys[norm] = candidate

    return keys


def slug_page_key(slug, config):
    """Return the stable output key for a slug."""
    norm = normalize_slug(slug)
    return config.get("_slug_page_keys", {}).get(norm, slug_basename(norm))


def slug_output_name(slug, config=None):
    """Return output HTML filename for a slug."""
    if config is None:
        return f"{slug}.html"
    key = slug_page_key(slug, config)
    return "index.html" if key == "index" else f"{key}.html"
