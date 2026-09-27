"""HTML pipeline: optimization, minification, and page building for fr-docs."""

import contextlib
import datetime
import json
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from .config_accessors import (
    copyright_holder,
    custom_tags,
    feature_enabled,
    features_state,
    footer_text,
    header_links,
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
    format_custom_tags,
    highlight_code_blocks,
    process_blockquotes,
)
from .template import TEMPLATE, build_toc_sidebar
from .utils import normalized_site_prefix, output_href


def _determine_tagged_sections(config):
    """Determine which sidebar sections should carry a custom tag.

    A section name containing ``[tag]`` (e.g. ``"[beta] New Features"``)
    is tagged with that tag. Returns a dict mapping section display name
    to its tag name. Sections without a tag are absent from the dict.
    """
    sidebar_config = sidebar(config)
    tags = custom_tags(config)
    tagged = {}
    for section_name, _ in sidebar_config:
        for tag in tags:
            if f"[{tag}]" in section_name:
                tagged[section_name] = tag
                break
    return tagged


def _get_logo_text(config):
    name = project_name(config)
    return name[0] if name else "Py"


def _get_copyright_year():
    return datetime.datetime.now(datetime.UTC).year


def _get_copyright_holder(config):
    return copyright_holder(config)


def _get_version_selector_html(config):
    if not feature_enabled(config, "versioning"):
        return ""
    return (
        '<div class="version-selector-wrap">'
        '  <select id="version-selector" class="version-selector" aria-label="Select version">'
        '    {config.get("_version_options", "")}'
        "  </select>"
        "</div>"
    )


def _get_header_search_html(config):
    if not feature_enabled(config, "search"):
        return ""
    return (
        '<svg class="header-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24" aria-hidden="true">'
        '  <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>'
        "</svg>"
        '<input type="text" id="header-search" placeholder="Search docs… (Ctrl+K)" autocomplete="off">'
        '<div id="search-results" class="search-results"></div>'
    )


def _get_header_nav_links(config):
    links = header_links(config)
    parts = []
    for item in links:
        name = item.get("name", "")
        href = item.get("href", "index.html")
        parts.append(f'<a href="{href}">{name}</a>')
    return "\n      ".join(parts)


def _get_footer_html(config):
    text = footer_text(config)
    if text:
        return text
    return (
        f"&copy; {_get_copyright_year()} {_get_copyright_holder(config)}"
        f" &middot; {project_name(config)} Documentation"
    )


def _get_search_preloads_html():
    return ""


def _render_template_placeholders(config):
    """Extract common template placeholders from config."""
    return {
        "site_prefix": output_href("", config),
        "page_title": "",
        "project_name": project_name(config),
        "og_title": "",
        "og_description": "",
        "logo_text": _get_logo_text(config),
        "version_selector_html": _get_version_selector_html(config),
        "header_search_html": _get_header_search_html(config),
        "header_nav_links": _get_header_nav_links(config),
        "extra_nav_links": "",
        "sidebar": "",
        "subtitle_html": "",
        "body": "",
        "search_index_inline": "",
        "search_preloads": _get_search_preloads_html(),
        "features_config_json": json.dumps(features_state(config)),
        "custom_tags_json": json.dumps(custom_tags(config)),
        "copyright_year": _get_copyright_year(),
        "copyright_holder": _get_copyright_holder(config),
        "footer_html": _get_footer_html(config),
    }


def should_absolutize_url(raw_url) -> bool:
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


def optimize_html(html_input):
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


def _extract_page_metadata(slug, body_md):
    """Extract page metadata from frontmatter."""
    meta, body_md = parse_frontmatter(body_md)
    title = meta.get("title", slug.capitalize())
    subtitle = meta.get("subtitle", "")
    page_title = meta.get("page_title", title).replace("[ext]", "").strip()
    og_title = meta.get("og_title", title).replace("[ext]", "").strip()
    return body_md, title, subtitle, page_title, og_title


def _render_backlinks_and_related(body_md, body_html, slug, config, search_index):
    """Render backlinks and related sections if applicable."""
    backlinks_html = ""
    related_html = ""
    if not search_index:
        return body_html, backlinks_html, related_html

    page_data = next(
        (p for p in search_index if slug in (p.get("slug"), p.get("source_slug"))),
        None,
    )
    if not page_data:
        return body_html, backlinks_html, related_html

    has_backlinks_tag = "<backlinks>" in body_md
    has_related_tag = "<related>" in body_md
    no_backlinks = "<!no_backlinks>" in body_md
    no_related = "<!no_related>" in body_md

    if (
        feature_enabled(config, "backlinks")
        and page_data.get("backlinks")
        and not no_backlinks
    ):
        backlinks_html = _render_backlinks(page_data["backlinks"], search_index)
        if has_backlinks_tag:
            body_html = body_html.replace("<p><backlinks></p>", backlinks_html)
            body_html = body_html.replace("<p><backlinks></p>\n", backlinks_html)
            body_html = body_html.replace("<backlinks>", backlinks_html)

    if (
        feature_enabled(config, "related")
        and page_data.get("related")
        and not no_related
    ):
        related_html = _render_related(page_data["related"], search_index)
        if has_related_tag:
            body_html = body_html.replace("<p><related></p>", related_html)
            body_html = body_html.replace("<p><related></p>\n", related_html)
            body_html = body_html.replace("<related>", related_html)

    return body_html, backlinks_html, related_html


def _apply_feature_transformations(body_html, config):
    """Apply feature-based HTML transformations."""
    if feature_enabled(config, "code_highlighting"):
        body_html = highlight_code_blocks(body_html)
    if feature_enabled(config, "blockquotes"):
        body_html = process_blockquotes(body_html)
    if feature_enabled(config, "ext_tags"):
        body_html = format_custom_tags(body_html, config)
    return body_html


def build_page(slug, config, slug_page_keys) -> None:
    """Build a single page from its markdown source."""
    src_path = Path(config["_src_dir"], f"{slug}.md")
    if not src_path.exists():
        print(f"  ⚠ Skipping {slug}.md (not found)")
        return

    raw = src_path.read_text(encoding="utf-8")
    body_md, title, subtitle, page_title, og_title = _extract_page_metadata(
        slug, raw
    )

    if config.get("search_map") and feature_enabled(config, "auto_link"):
        body_md = auto_link_markdown(body_md, config["search_map"])

    body_html, toc_tokens = convert_markdown(body_md)
    body_html = rewrite_md_links(body_html, slug, slug_page_keys)

    if feature_enabled(config, "auto_link"):
        body_html = auto_link_filenames(body_html, config.get("_slug_page_keys", {}))

    code_refs = []
    if feature_enabled(config, "code_references"):
        body_html, code_refs = process_code_references_html(body_html, config)

    body_html = _apply_feature_transformations(body_html, config)

    search_index = config.get("_search_index", [])
    body_html, _backlinks_html, _related_html = _render_backlinks_and_related(
        body_md, body_html, slug, config, search_index
    )

    subtitle_html = f'<p class="subtitle">{subtitle}</p>' if subtitle else ""
    tagged_sections = _determine_tagged_sections(config)
    sidebar_html = build_toc_sidebar(
        toc_tokens, slug, sidebar(config), tagged_sections, config
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
    out_path = Path(config["_out_dir"], out_name)
    out_path.write_text(out_html, encoding="utf-8")


def _strip_site_prefix(out_dir, stripped_prefix, backed_up):
    """Strip site prefix from HTML files and back them up."""
    if not stripped_prefix:
        return

    prefix_pat = re.compile(
        rf'href=(["\']?){re.escape(stripped_prefix)}/([^"\'\s>]+)\1'
    )
    for html_file in out_dir.glob("*.html"):
        raw = html_file.read_text(encoding="utf-8")
        backup = out_dir / f".critical_orig_{html_file.stem}.html"
        backup.write_text(raw, encoding="utf-8")
        backed_up.append(backup)
        rewritten = prefix_pat.sub(
            lambda m: f"href={m.group(1)}{m.group(2)}{m.group(1)}",
            raw,
        )
        html_file.write_text(rewritten, encoding="utf-8")


def _run_critical_on_file(html_file, out_dir):
    """Run critical on a single HTML file."""
    cmd = [
        "npx",
        "critical",
        str(html_file),
        "--inline",
        "--engine",
        "static",
        "--dimensions",
        "390x844,1920x1080",
        "--width",
        "1920",
        "--height",
        "1080",
    ]

    result = subprocess.run(
        cmd, capture_output=True, text=True, check=False, cwd=str(out_dir)
    )
    if result.returncode != 0:
        msg = f"Critical failed for {html_file.name}:\n{result.stderr}"
        raise RuntimeError(msg)

    optimized = result.stdout
    if "</html>" not in optimized:
        msg = f"Critical output for {html_file.name} looks truncated"
        raise RuntimeError(msg)

    html_file.write_text(optimized, encoding="utf-8")


def _restore_backups(out_dir, backed_up):
    """Restore original HTML for pages critical didn't inline, and clean up backups."""
    for backup in backed_up:
        target = out_dir / f"{backup.stem.replace('.critical_orig_', '')}.html"
        if target.exists() and backup.exists():
            target_content = target.read_text(encoding="utf-8")
            if "data-critical" not in target_content:
                target.write_text(
                    backup.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
        with contextlib.suppress(OSError):
            backup.unlink()


def optimize_all_pages(config) -> None:
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

    site_prefix = normalized_site_prefix(config)
    stripped_prefix = (
        site_prefix.rstrip("/") if site_prefix and site_prefix != "/" else None
    )
    backed_up = []

    try:
        _strip_site_prefix(out_dir, stripped_prefix, backed_up)
        for html_file in out_dir.glob("*.html"):
            _run_critical_on_file(html_file, out_dir)
    finally:
        _restore_backups(out_dir, backed_up)


def minify_all_pages(config) -> None:
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
        if re.search(r"\brel\s*=", attrs, re.IGNORECASE):
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


def _render_backlinks(backlinks, search_index) -> str:
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
    return (
        f"<h2>Backlinks</h2>"
        f'<details class="backlinks-details">'
        f"  <summary>"
        f"    Show {len(items)} backlinks"
        f"  </summary>"
        f"  <ul>"
        f"    {''.join(items)}"
        f"  </ul>"
        f"</details>"
    )


def _render_related(related, search_index) -> str:
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

    return (
        f'<h2>Related</h2><div class="related">  <ul>    {"".join(items)}  </ul></div>'
    )
