"""Search index building for fr-docs."""

import os
import re

from .frontmatter import parse_frontmatter
from .slug import normalize_slug, slug_output_name, slug_page_key
from .utils import output_href


def _parse_search_sections(body_md):
    """Extract searchable text sections from markdown body."""
    title = None
    current_heading = title

    sections = []
    in_table = False

    table_first_cols = []
    table_header_seen = False

    for line in body_md.split("\n"):
        stripped = line.strip()

        if stripped.startswith("|") and "|" in stripped[1:]:
            if re.match(r"^\|[\s\-:|]+\|$", stripped):
                table_header_seen = True
                continue

            if not in_table:
                in_table = True
                table_header_seen = False
                continue

            if not table_header_seen:
                continue

            if cols := [c.strip() for c in stripped.strip("|").split("|")]:
                if col := re.sub(r"[`*\[\]()]", "", cols[0]).strip():
                    table_first_cols.append(col)

            continue

        else:
            if in_table and table_first_cols:
                sections.append(
                    {
                        "heading": current_heading,
                        "text": ", ".join(table_first_cols),
                    }
                )
                table_first_cols = []

            in_table = False
            table_header_seen = False

        if stripped.startswith("#"):
            current_heading = stripped.lstrip("#").strip()

        elif (stripped
                and not stripped.startswith("```")
                and not stripped.startswith("---")
            ):
            if clean := re.sub(r"[`*\[\]()]", "", stripped):
                sections.append({"heading": current_heading, "text": clean})

    if table_first_cols:
        sections.append(
            {"heading": current_heading, "text": ", ".join(table_first_cols)}
        )

    return sections


def build_search_index(slugs, config):
    """Build the search index from markdown sources."""
    search_index = []

    for slug in slugs:
        src = os.path.join(config["_src_dir"], f"{slug}.md")

        if os.path.exists(src):
            with open(src, "r", encoding="utf-8") as f:
                raw = f.read()

            meta, body_md = parse_frontmatter(raw)

            title = meta.get("title", slug.capitalize())
            sections = _parse_search_sections(body_md)

            page_key = slug_page_key(slug, config)
            url = output_href(slug_output_name(slug, config), config)
            search_index.append(
                {
                    "slug": page_key,
                    "source_slug": normalize_slug(slug),
                    "title": title,
                    "url": url,
                    "sections": sections,
                }
            )

    config["search_map"] = {}
    for item in search_index:
        title = item.get("title") or ""
        source_slug = item.get("source_slug") or item.get("slug")
        if not title or not source_slug:
            continue

        cleaned = re.sub(r"\[ext\]", "", title)
        cleaned = re.sub(r"[`*()]+", "", cleaned).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)

        config["search_map"][cleaned] = f"{source_slug}.md"
        if title != cleaned:
            config["search_map"][title] = f"{source_slug}.md"

    return search_index
