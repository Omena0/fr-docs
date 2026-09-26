"""HTML template for documentation pages."""

import re

from .config_accessors import feature_enabled
from .slug import slug_basename, slug_output_name

TEMPLATE = """\
<!DOCTYPE html>
<html lang="en" data-site-prefix="{site_prefix}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{page_title} — {project_name}</title>
  <meta property="og:title" content="{og_title} — {project_name}">
  <meta name="description" content="{og_description}">
  <meta property="og:description" content="{og_description}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{project_name} Docs">
  <meta name="theme-color" content="#6366f1">
  <meta name="color-scheme" content="dark">
  <link rel="icon" href="{site_prefix}favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="{site_prefix}style.css">
  <link rel="stylesheet" href="{site_prefix}fonts.css" media="print" onload="this.media='all'">
</head>
<body>
  <!-- Header -->
  <header class="site-header">
    <button class="menu-toggle" aria-label="Toggle menu">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24" aria-hidden="true">
        <path d="M3 12h18M3 6h18M3 18h18"/>
      </svg>
    </button>
    <div class="header-brand-row">
      <a href="index.html" class="header-brand">
          <span class="logo">{logo_text}</span>
          {project_name}
      </a>
      {version_selector_html}
    </div>
    <div class="header-search">
      {header_search_html}
    </div>
    <nav class="header-nav">
      {header_nav_links}
    </nav>
  </header>

  <!-- Sidebar -->
  <aside class="sidebar">
{sidebar}
  </aside>
  <div class="sidebar-overlay"></div>

  <!-- Main -->
  <main class="main">
    <div class="content">
      {subtitle_html}
      {body}
    </div>
    <footer class="site-footer">
      {footer_html}
    </footer>
  </main>

  <!-- Back to top -->
  <button class="back-to-top" aria-label="Back to top">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
        <path d="M18 15l-6-6-6 6"/>
      </svg>
    </button>

    {search_index_inline}
    <script id="code-refs-data" type="application/json">{code_refs_json}</script>
    <script id="search-config" type="application/json">{search_config_json}</script>
    <script id="features-config" type="application/json">{features_config_json}</script>
    <script id="custom-tags-config" type="application/json">{custom_tags_json}</script>
    <script src="{site_prefix}script.js" defer></script>
</body>
</html>
"""


def build_sidebar_html(current_slug, sidebar_config, tagged_sections=None, config=None):
    """Generate the sidebar HTML from the config sidebar definition.

    ``tagged_sections`` maps a section's display name to its custom-tag
    name (e.g. ``{"[beta] New Features": "beta"}``). The ``[tag]``
    prefix is stripped from the heading text and a badge is appended.\n
        :param current_slug: Current page slug
        :type current_slug: str
        :param sidebar_config: Sidebar configuration
        :type sidebar_config: list[tuple]
        :param tagged_sections: Tagged sections mapping
        :type tagged_sections: dict[str, str] | None
        :param config: Configuration dictionary
        :type config: dict | None
        :return: Sidebar HTML string
        :rtype: str
    """
    if tagged_sections is None:
        tagged_sections = {}

    parts = []
    if config and feature_enabled(config, "search"):
        parts.extend(
            [
                '<div class="search-box">',
                '  <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20" aria-hidden="true">',
                '    <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
                "  </svg>",
                '  <input type="text" id="sidebar-search" placeholder="Search docs…">',
                "</div>",
            ]
        )

    for section_name, pages in sidebar_config:
        key = _section_key(section_name)
        tag = tagged_sections.get(section_name)
        heading = section_name
        tag_badge = ""
        if tag:
            # Strip the [tag] prefix from the heading text
            heading = re.sub(r"^\s*\[[^\]]+\]\s*", "", section_name).strip()
            tag_badge = f' <span class="ext-tag">{tag}</span>'

        # Auto-expand the section that contains the current page, and
        # any section with only one page (so users can see its contents
        # without clicking). If there's only one section total, expand
        # it regardless.
        contains_current = any(slug == current_slug for slug, _ in pages)
        only_section = len(sidebar_config) == 1
        collapsed = not (contains_current or only_section or len(pages) <= 1)

        parts.extend(
            (
                '<div class="sidebar-section">',
                f'  <div class="sidebar-heading{" collapsed" if collapsed else ""}" data-section="{key}">{heading}{tag_badge}',
                '  <ul class="sidebar-links">',
            )
        )
        for slug, label in pages:
            active = ' class="active"' if slug == current_slug else ""
            href = slug_output_name(slug_basename(slug))
            display = label
            parts.append(f'    <li><a href="{href}"{active}>{display}</a></li>')

        parts.extend(("  </ul>", "</div>"))

    return "\n".join(parts)


def build_toc_sidebar(
    toc_tokens, current_slug, sidebar_config, tagged_sections=None, config=None
):
    """Build the sidebar with 'On This Page' TOC at the top, then nav sections.\n
        :param toc_tokens: Table of contents tokens
        :type toc_tokens: list[dict]
        :param current_slug: Current page slug
        :type current_slug: str
        :param sidebar_config: Sidebar configuration
        :type sidebar_config: list[tuple]
        :param tagged_sections: Tagged sections mapping
        :type tagged_sections: dict[str, str] | None
        :param config: Configuration dictionary
        :type config: dict | None
        :return: Combined sidebar HTML
        :rtype: str
    """
    nav = build_sidebar_html(current_slug, sidebar_config, tagged_sections, config)
    if not toc_tokens:
        return nav

    toc_parts = [
        '<div class="sidebar-section">',
        '  <div class="sidebar-heading" data-section="on-this-page">On This Page</div>',
        '  <ul class="sidebar-links">',
    ]
    for token in toc_tokens:
        toc_parts.append(f'    <li><a href="#{token["id"]}">{token["name"]}</a></li>')
        if children := token.get("children", []):
            toc_parts.append(
                f'    <li><ul class="toc-sub" data-parent="{token["id"]}">'
            )
            toc_parts.extend(
                f'      <li><a href="#{child["id"]}">{child["name"]}</a></li>'
                for child in children
            )
            toc_parts.append("    </ul></li>")

    toc_parts.extend(("  </ul>", "</div>"))

    search_end = nav.find("</div>") + len("</div>")
    return nav[:search_end] + "\n" + "\n".join(toc_parts) + "\n" + nav[search_end:]


def _section_key(name):
    import re

    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")