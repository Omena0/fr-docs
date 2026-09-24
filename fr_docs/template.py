"""HTML template for documentation pages."""

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
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,400..800&family=JetBrains+Mono:wght@400..700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <!-- Header -->
  <header class="site-header">
    <button class="menu-toggle" aria-label="Toggle menu">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M3 12h18M3 6h18M3 18h18"/>
      </svg>
    </button>
    <div class="header-brand-row">
      <a href="index.html" class="header-brand">
          <span class="logo">{logo_text}</span>
          {project_name}
      </a>
      <div class="version-selector-wrap">
          <select id="version-selector" class="version-selector" aria-label="Select version">
              {version_options}
          </select>
      </div>
    </div>
    <div class="header-search">
      <svg class="header-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
      <input type="text" id="header-search" placeholder="Search docs… (Ctrl+K)" autocomplete="off">
      <div id="search-results" class="search-results"></div>
    </div>
    <nav class="header-nav">
      <a href="index.html">Docs</a>
      {extra_nav_links}
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
      &copy; {copyright_year} {copyright_holder} &middot; {project_name} Documentation
    </footer>
  </main>

  <!-- Back to top -->
  <button class="back-to-top" aria-label="Back to top">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <path d="M18 15l-6-6-6 6"/>
    </svg>
  </button>

    {search_index_inline}
    <script src="script.js" defer></script>
</body>
</html>
"""


def build_sidebar_html(current_slug, sidebar_config, ext_sections=None):
    """Generate the sidebar HTML from the config sidebar definition."""
    if ext_sections is None:
        ext_sections = {"Extensions"}

    parts = [
        '<div class="search-box">',
        '  <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>',
        '  <input type="text" id="sidebar-search" placeholder="Search docs…">',
        '</div>',
    ]

    for section_name, pages in sidebar_config:
        key = _section_key(section_name)
        is_ext = section_name in ext_sections
        parts.extend(
            (
                '<div class="sidebar-section">',
                f'  <div class="sidebar-heading collapsed" data-section="{key}">{section_name}</div>',
                '  <ul class="sidebar-links">',
            )
        )
        for slug, label in pages:
            active = ' class="active"' if slug == current_slug else ''
            href = slug_output_name(slug)
            display = f'{label} <span class="ext-tag">ext</span>' if is_ext else label
            parts.append(f'    <li><a href="{href}"{active}>{display}</a></li>')

        parts.extend(('  </ul>', '</div>'))

    return "\n".join(parts)


def build_toc_sidebar(toc_tokens, current_slug, sidebar_config, ext_sections=None):
    """Build the sidebar with 'On This Page' TOC at the top, then nav sections."""
    nav = build_sidebar_html(current_slug, sidebar_config, ext_sections)
    if not toc_tokens:
        return nav

    toc_parts = [
        '<div class="sidebar-section">',
        '  <div class="sidebar-heading" data-section="on-this-page">On This Page</div>',
        '  <ul class="sidebar-links">',
    ]
    for token in toc_tokens:
        toc_parts.append(f'    <li><a href="#{token["id"]}">{token["name"]}</a></li>')
        children = token.get("children", [])
        if children:
            toc_parts.append(f'    <li><ul class="toc-sub" data-parent="{token["id"]}">')
            toc_parts.extend(
                f'      <li><a href="#{child["id"]}">{child["name"]}</a></li>'
                for child in children
            )
            toc_parts.append('    </ul></li>')

    toc_parts.extend(('  </ul>', '</div>'))

    search_end = nav.find('</div>') + len('</div>')
    return nav[:search_end] + '\n' + '\n'.join(toc_parts) + '\n' + nav[search_end:]


def _section_key(name):
    import re
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


# These will be imported from the main build module
def slug_output_name(slug):
    return f"{slug}.html"


def slug_page_key(slug):
    return slug


def _normalize_slug(slug):
    return str(slug).replace("\\", "/").strip("/")


def slug_basename(slug):
    normalized = str(slug).replace("\\", "/").strip("/")
    if not normalized:
        return ""
    return normalized.rsplit("/", 1)[-1]