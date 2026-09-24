"""HTML pipeline: optimization, minification, and page building for fr-docs."""

import datetime
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from .config_accessors import (
    minify_html as cfg_minify_html,
)
from .config_accessors import (
    optimize_html as cfg_optimize_html,
)
from .config_accessors import (
    project_name,
    sidebar,
)
from .frontmatter import parse_frontmatter
from .markdown import (
    auto_link_markdown,
    convert_markdown,
    rewrite_md_links,
)
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
    for section_name, _ in sidebar_config:
        if "[ext]" in section_name:
            ext_sections.append(section_name)
    return ext_sections if ext_sections else {"Extensions"}


def _render_template_placeholders(config):
    """Extract common template placeholders from config."""

    def _get_logo_text():
        name = project_name(config)
        return name[0] if name else "Py"

    def _get_copyright_year():
        return datetime.datetime.now(datetime.UTC).year

    def _get_copyright_holder():
        if "Omena0" in project_name(config):
            return "Omena0"
        return project_name(config)

    return {
        "site_prefix": output_href("", config),
        "page_title": "",
        "project_name": project_name(config),
        "og_title": "",
        "og_description": "",
        "logo_text": _get_logo_text(),
        "version_options": "",
        "extra_nav_links": "",
        "sidebar": "",
        "subtitle_html": "",
        "body": "",
        "search_index_inline": "",
        "copyright_year": _get_copyright_year(),
        "copyright_holder": _get_copyright_holder(),
    }


def should_absolutize_url(raw_url):
    if not raw_url:
        return False
    value = raw_url.strip()
    if not value or value.startswith(("#", "//")):
        return False
    if re.search(r"\.(css|js|svg|png|jpg|jpeg|gif|ico|woff|woff2|ttf|eot)$", value, re.I):
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
            and not absolute.startswith(prefix + "/")
        ):
            absolute = prefix + absolute
        if parts.query:
            absolute += f"?{parts.query}"
        if parts.fragment:
            absolute += f"#{parts.fragment}"
        if quote:
            return f"{attr}={quote}{absolute}{quote}"
        return f"{attr}={absolute}"

    return URL_ATTR_RE.sub(_repl, html_text)


def optimize_html(html_input, config):
    if not config.get("production", False):
        return html_input
    if not cfg_optimize_html(config):
        return html_input

    with tempfile.NamedTemporaryFile("w+", suffix=".html", delete=False) as f_in:
        f_in.write(html_input)
        in_path = Path(f_in.name)

    cmd = [
        "npx",
        "critical",
        str(in_path),
        "--inline",
        "--width",
        "1920",
        "--height",
        "1080",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    try:
        if result.returncode != 0:
            raise RuntimeError(f"Critical failed:\n{result.stderr}")

        optimized_html = result.stdout

        if "</html>" not in optimized_html:
            raise RuntimeError("Critical output looks truncated/corrupted")

        return optimized_html

    finally:
        try:
            in_path.unlink()
        except OSError:
            pass


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

    if config.get("search_map"):
        body_md = auto_link_markdown(body_md, config["search_map"])

    body_html, toc_tokens = convert_markdown(body_md)
    body_html = rewrite_md_links(body_html, slug, slug_page_keys)
    body_html = highlight_code_blocks(body_html)
    body_html = process_blockquotes(body_html)
    body_html = format_ext_tags(body_html)

    subtitle_html = f'<p class="subtitle">{subtitle}</p>' if subtitle else ""

    ext_sections = _determine_ext_sections(config)
    sidebar_html = build_toc_sidebar(toc_tokens, slug, sidebar(config), ext_sections)

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
        }
    )

    out_html = TEMPLATE.format(**placeholders)

    try:
        out_html = optimize_html(out_html, config)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to optimize HTML: {e}")

    try:
        out_html = minify_html(out_html, config)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to minify HTML: {e}")

    if config.get("production", False):
        page_url = (
            f"https://docs.local{output_href(slug_output_name(slug, config), config)}"
        )
        out_html = absolutize_links(out_html, page_url, config)

    out_name = slug_output_name(slug, config)
    out_path = os.path.join(config["_out_dir"], out_name)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out_html)


logger = logging.getLogger(__name__)
