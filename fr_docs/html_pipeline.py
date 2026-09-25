"""HTML pipeline: optimization, minification, and page building for fr-docs."""

import datetime
import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from .config_accessors import (
    copyright_holder,
    feature_enabled,
    project_name,
    sidebar,
)
from .config_accessors import (
    minify_html as cfg_minify_html,
)
from .config_accessors import (
    optimize_html as cfg_optimize_html,
)
from .frontmatter import parse_frontmatter
from .markdown import (
    auto_link_filenames,
    auto_link_markdown,
    convert_markdown,
    process_code_references_html,
    rewrite_md_links,
)
from .search import search_include_config
from .slug import slug_output_name
from .syntax import (
    URL_ATTR_RE,
    format_ext_tags,
    highlight_code_blocks,
    process_blockquotes,
)
from .template import TEMPLATE, build_toc_sidebar
from .utils import normalized_site_prefix, output_href


def _determine_ext_sections(config):
    """Determine which sections should have the [ext] tag."""
    sidebar_config = sidebar(config)
    ext_sections = []
    ext_sections.extend(
        section_name for section_name, _ in sidebar_config if "[ext]" in section_name
    )
    return ext_sections or {"Extensions"}


def _render_template_placeholders(config):
    """Extract common template placeholders from config."""

    def _get_logo_text():
        name = project_name(config)
        return name[0] if name else "Py"

    def _get_copyright_year():
        return datetime.datetime.now(datetime.UTC).year

    def _get_copyright_holder():
        return copyright_holder(config)

    def _get_version_selector_html():
        if not feature_enabled(config, "versioning"):
            return ""
        return f"""<div class="version-selector-wrap">
          <select id="version-selector" class="version-selector" aria-label="Select version">
              {config.get("_version_options", "")}
          </select>
      </div>"""

    def _get_header_search_html():
        if not feature_enabled(config, "search"):
            return ""
        return """<svg class="header-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24" aria-hidden="true"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
      <input type="text" id="header-search" placeholder="Search docs… (Ctrl+K)" autocomplete="off">
      <div id="search-results" class="search-results"></div>"""

    def _get_search_preloads_html():
        return ""

    return {
        "site_prefix": output_href("", config),
        "page_title": "",
        "project_name": project_name(config),
        "og_title": "",
        "og_description": "",
        "logo_text": _get_logo_text(),
        "version_selector_html": _get_version_selector_html(),
        "header_search_html": _get_header_search_html(),
        "extra_nav_links": "",
        "sidebar": "",
        "subtitle_html": "",
        "body": "",
        "search_index_inline": "",
        "search_preloads": _get_search_preloads_html(),
        "copyright_year": _get_copyright_year(),
        "copyright_holder": _get_copyright_holder(),
    }


def should_absolutize_url(raw_url):
    if not raw_url:
        return False
    value = raw_url.strip()
    if not value or value.startswith(("#", "//")):
        return False
    if re.search(
        r"\.(css|js|svg|png|jpg|jpeg|gif|ico|woff|woff2|ttf|eot)$", value, re.IGNORECASE
    ):
        return False
    return not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", value)


def absolutize_links(html_text, page_url, config):
    if not html_text or not page_url:
        return html_text

    prefix = normalized_site_prefix(config).rstrip("/") or "/"

    def _repl(m):
        attr = m.group("attr")
        quote = m.group("quote")
        raw_url = m.group("url")
        if not should_absolutize_url(raw_url):
            return m.group(0)
        resolved = urljoin(page_url, raw_url)
        parts = urlsplit(resolved)
        absolute = parts.path or "/"
        if (
            prefix != "/"
            and absolute.startswith("/")
            and absolute != prefix
            and not absolute.startswith(f"{prefix}/")
        ):
            absolute = prefix + absolute
        if parts.query:
            absolute += f"?{parts.query}"
        if parts.fragment:
            absolute += f"#{parts.fragment}"
        return f"{attr}={quote}{absolute}{quote}" if quote else f"{attr}={absolute}"

    return URL_ATTR_RE.sub(_repl, html_text)


def optimize_html(html_input, config):
    """Legacy single-file optimizer — kept for backwards compat.

    critical only resolves <link rel=stylesheet> URLs when run on a
    directory, so this is a no-op in production. Use optimize_all_pages
    instead.
    """
    return html_input


def minify_html(html_input, config):
    if not config.get("production", False):
        return html_input
    if not cfg_minify_html(config):
        return html_input

    with tempfile.NamedTemporaryFile("w+", suffix=".html", delete=False) as temp_in:
        temp_in.write(html_input)
        temp_in_path = Path(temp_in.name)

    with tempfile.NamedTemporaryFile("r+", suffix=".html", delete=False) as temp_out:
        temp_out_path = Path(temp_out.name)

    cmd = [
        "npx",
        "html-minifier-next",
        "--minify-css",
        "true",
        "--minify-js",
        "true",
        "--minify-svg",
        "true",
        "--minify-urls",
        "true",
        "--remove-attribute-quotes",
        "--collapse-whitespace",
        "--remove-tag-whitespace",
        "--remove-comments",
        "-o",
        str(temp_out_path),
        str(temp_in_path),
    ]

    subprocess.run(cmd, check=True, capture_output=True, text=True)

    minified_html = temp_out_path.read_text(encoding="utf-8")

    temp_in_path.unlink()
    temp_out_path.unlink()

    return minified_html


def build_page(slug, config, slug_page_keys):
    """Build a single page from its markdown source."""
    src_path = os.path.join(config["_src_dir"], f"{slug}.md")
    if not os.path.exists(src_path):
        print(f"  ⚠ Skipping {slug}.md (not found)")
        return

    with open(src_path, "r", encoding="utf-8") as f:
        raw = f.read()

    meta, body_md = parse_frontmatter(raw)
    title = meta.get("title", slug.capitalize())
    subtitle = meta.get("subtitle", "")
    page_title = meta.get("page_title", title).replace("[ext]", "").strip()
    og_title = meta.get("og_title", title).replace("[ext]", "").strip()

    if config.get("search_map") and feature_enabled(config, "auto_link"):
        body_md = auto_link_markdown(body_md, config["search_map"])

    body_html, toc_tokens = convert_markdown(body_md)
    body_html = rewrite_md_links(body_html, slug, slug_page_keys)

    # Auto-link bare filename references (e.g., config.json -> config.json.md)
    if feature_enabled(config, "auto_link"):
        body_html = auto_link_filenames(
            body_html, slug, config.get("_slug_page_keys", {})
        )

    # Process code references (in HTML, after markdown conversion)
    code_refs = []
    if feature_enabled(config, "code_references"):
        body_html, code_refs = process_code_references_html(body_html, config)

    if feature_enabled(config, "code_highlighting"):
        body_html = highlight_code_blocks(body_html)
    if feature_enabled(config, "blockquotes"):
        body_html = process_blockquotes(body_html)
    if feature_enabled(config, "ext_tags"):
        body_html = format_ext_tags(body_html)

    # Handle <backlinks> and <related> tags
    backlinks_html = ""
    related_html = ""
    search_index = config.get("_search_index", [])
    if search_index and (
        page_data := next(
            (
                p
                for p in search_index
                if p.get("slug") == slug or p.get("source_slug") == slug
            ),
            None,
        )
    ):
        # Check for tags in original markdown
        has_backlinks_tag = "<backlinks>" in body_md
        has_related_tag = "<related>" in body_md
        # Check for disable tags
        no_backlinks = "<!no_backlinks>" in body_md
        no_related = "<!no_related>" in body_md

        if (
            feature_enabled(config, "backlinks")
            and page_data.get("backlinks")
            and not no_backlinks
        ):
            backlinks_html = _render_backlinks(
                page_data["backlinks"], search_index, config
            )
            if has_backlinks_tag:
                # Replace both paragraph-wrapped and bare tag
                body_html = body_html.replace("<p><backlinks></p>", backlinks_html)
                body_html = body_html.replace("<p><backlinks></p>\n", backlinks_html)
                body_html = body_html.replace("<backlinks>", backlinks_html)

        if (
            feature_enabled(config, "related")
            and page_data.get("related")
            and not no_related
        ):
            related_html = _render_related(page_data["related"], search_index, config)
            if has_related_tag:
                # Replace both paragraph-wrapped and bare tag
                body_html = body_html.replace("<p><related></p>", related_html)
                body_html = body_html.replace("<p><related></p>\n", related_html)
                body_html = body_html.replace("<related>", related_html)

    subtitle_html = f'<p class="subtitle">{subtitle}</p>' if subtitle else ""

    ext_sections = _determine_ext_sections(config)
    sidebar_html = build_toc_sidebar(
        toc_tokens, slug, sidebar(config), ext_sections, config
    )

    og_description = subtitle or f"{title} — {project_name(config)} documentation"

    placeholders = _render_template_placeholders(config)
    placeholders.update(
        {
            "page_title": page_title,
            "og_title": og_title,
            "og_description": og_description,
            "subtitle_html": subtitle_html,
            "sidebar": sidebar_html,
            "body": body_html,
            "code_refs_json": json.dumps(code_refs),
            "search_config_json": json.dumps(search_include_config(config)),
        }
    )

    out_html = TEMPLATE.format(**placeholders)

    if config.get("production", False):
        page_url = (
            f"https://docs.local{output_href(slug_output_name(slug, config), config)}"
        )
        out_html = absolutize_links(out_html, page_url, config)
        out_html = add_internal_prefetch_links(out_html, config)

    out_name = slug_output_name(slug, config)
    out_path = os.path.join(config["_out_dir"], out_name)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out_html)


def optimize_all_pages(config):
    """Inline critical-path CSS into every production HTML page.

    critical only resolves <link rel=stylesheet> URLs when run on a
    single HTML file with the static engine (directory mode reports
    "no stylesheets discovered" regardless of engine). Running it on a
    single temp file reports "no stylesheets discovered" and silently
    passes through — which on a slow 4G connection means FCP is gated
    by the full CSS download (~4s for 7.6KB at 1.6Mbps).

    Must be called once after all pages are written, not from within
    build_page (which runs in a thread pool).
    """
    if not config.get("production", False):
        return
    if not cfg_optimize_html(config):
        return

    out_dir = Path(config["_out_dir"]).resolve()
    if not out_dir.is_dir():
        return

    # critical only follows relative stylesheet URLs from each HTML
    # file's location. The production template uses absolute paths
    # (e.g. href=/fr-docs/style.css), so rewrite them to relative
    # paths first, run critical, then restore the absolute paths in
    # the inlined output.
    site_prefix = normalized_site_prefix(config)
    stripped_prefix = site_prefix.rstrip("/") if site_prefix and site_prefix != "/" else None
    backed_up = []

    try:
        if stripped_prefix:
            # Match both quoted (href="/fr-docs/style.css") and unquoted
            # (href=/fr-docs/style.css) forms. The minifier strips quotes,
            # so both must be supported.
            prefix_pat = re.compile(
                rf'href=(["\']?){re.escape(stripped_prefix)}/([^"\'\s>]+)\1'
            )
            for html_file in out_dir.glob("*.html"):
                raw = html_file.read_text(encoding="utf-8")
                backup = out_dir / f".critical_orig_{html_file.stem}.html"
                backup.write_text(raw, encoding="utf-8")
                backed_up.append(backup)
                # Strip the site prefix so href=/fr-docs/style.css
                # becomes href=style.css (relative to the HTML file).
                rewritten = prefix_pat.sub(
                    lambda m: f'href={m.group(1)}{m.group(2)}{m.group(1)}',
                    raw,
                )
                html_file.write_text(rewritten, encoding="utf-8")

        # Run critical per-file with the static engine (the only engine
        # that resolves relative stylesheet URLs from a single file).
        for html_file in out_dir.glob("*.html"):
            cmd = [
                "npx",
                "critical",
                str(html_file),
                "--inline",
                "--engine",
                "static",
                "--width",
                "1920",
                "--height",
                "1080",
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, cwd=str(out_dir)
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Critical failed for {html_file.name}:\n{result.stderr}"
                )

            optimized = result.stdout
            if "</html>" not in optimized:
                raise RuntimeError(
                    f"Critical output for {html_file.name} looks truncated"
                )

            html_file.write_text(optimized, encoding="utf-8")

    finally:
        # Restore the original absolute-path HTML for any page critical
        # didn't inline (e.g. it failed or skipped).
        for backup in backed_up:
            target = out_dir / f"{backup.stem.replace('.critical_orig_', '')}.html"
            if target.exists() and backup.exists():
                try:
                    target_content = target.read_text(encoding="utf-8")
                    # Only restore if critical didn't inline CSS
                    if "data-critical" not in target_content:
                        target.write_text(
                            backup.read_text(encoding="utf-8"),
                            encoding="utf-8",
                        )
                except OSError:
                    pass
            try:
                backup.unlink()
            except OSError:
                pass


def minify_all_pages(config):
    """Minify every production HTML page after critical has inlined CSS."""
    if not config.get("production", False):
        return
    if not cfg_minify_html(config):
        return

    out_dir = Path(config["_out_dir"]).resolve()
    if not out_dir.is_dir():
        return

    for html_file in sorted(out_dir.glob("*.html")):
        try:
            raw = html_file.read_text(encoding="utf-8")
            minified = minify_html(raw, config)
            html_file.write_text(minified, encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to minify {html_file.name}: {e}")


def add_internal_prefetch_links(html_text, config):
    """Add rel="prefetch" to every internal page link in production HTML.

    Prefetching the whole site up front is cheap here (a handful of small
    pages) and makes navigation instant. We deliberately avoid
    <link rel="preload" as="document">: Chrome's preload scanner rejects
    dynamically-injected document preloads, and rel="prefetch" is the
    correct hint for "fetch this page for later navigation".
    """
    if not config.get("production", False):
        return html_text

    href_re = re.compile(
        r'href\s*=\s*(?:"(?P<q1>[^"]*)"|\'(?P<q2>[^\']*)\'|(?P<uq>[^\s>]+))'
    )

    # Match the opening <a ...> tag only. attrs must not contain a bare '>'
    # (quoted values are allowed), so the match always stops at the first
    # unquoted '>', which is exactly the closing '>' of the <a> opening
    # tag. This is safe because an opening <a> tag cannot legitimately
    # contain another start tag.
    tag_re = re.compile(
        r'<a\s+(?P<attrs>(?:[^>"\']|"[^"]*"|\'[^\']*\')*)>',
    )

    def _repl(m):
        attrs = m.group("attrs")
        # Skip links that already declare a rel attribute
        if re.search(r'\brel\s*=', attrs, re.IGNORECASE):
            return m.group(0)
        hm = href_re.search(attrs)
        if not hm:
            return m.group(0)
        href = hm.group("q1") or hm.group("q2") or hm.group("uq") or ""
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            return m.group(0)
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", href):
            return m.group(0)
        # Only prefetch same-origin HTML pages (skip assets, anchors, etc.)
        if not re.search(r"\.(?:html?|htm)$", href, re.IGNORECASE):
            return m.group(0)
        # Insert rel="prefetch" right after "<a " so the closing '>' and
        # any trailing attributes are preserved verbatim.
        return m.group(0).replace("<a ", '<a rel="prefetch" ', 1)

    return tag_re.sub(_repl, html_text)


logger = logging.getLogger(__name__)


def _render_backlinks(backlinks, search_index, config):
    """Render backlinks HTML."""
    if not backlinks:
        return ""
    items = []
    for bl_slug in backlinks:
        if page := next((p for p in search_index if p.get("slug") == bl_slug), None):
            url = page.get("url", f"{bl_slug}.html")
            title = page.get("title", bl_slug)
            items.append(f'<li><a href="{url}">{title}</a></li>')
    if not items:
        return ""
    return f"""<h2>Backlinks</h2>
<details class="backlinks-details">
  <summary>Show {len(items)} backlinks</summary>
  <ul>
    {"".join(items)}
  </ul>
</details>"""


def _render_related(related, search_index, config):
    """Render related pages HTML."""
    if not related:
        return ""
    items = []
    for rel_slug in related:
        if page := next((p for p in search_index if p.get("slug") == rel_slug), None):
            url = page.get("url", f"{rel_slug}.html")
            title = page.get("title", rel_slug)
            items.append(f'<li><a href="{url}">{title}</a></li>')
    if not items:
        return ""
    return f"""<h2>Related</h2>
<div class="related">
  <ul>
    {"".join(items)}
  </ul>
</div>"""
