#!/usr/bin/env python3
"""
Build script for the fr-docs documentation site.
Converts Markdown source files into a static HTML site using configuration.
"""

import argparse
import base64
import concurrent.futures
from pathlib import Path
import subprocess
import tempfile
import shutil
import html
import os
import posixpath
import re
import threading
from urllib.parse import urljoin, urlsplit
import sys

# Import local modules
from fr_docs.config import load_config, project_name, site_prefix, sidebar, src_dir, out_dir, docs_dir, search_index_filename, git_meta_filename, zstd_level, workers, minify_html as cfg_minify_html, optimize_html as cfg_optimize_html, commit_message_pattern, live_label, project_url, src_map_path
from fr_docs.template import TEMPLATE, build_sidebar_html, build_toc_sidebar

try:
    import markdown
    from markdown.extensions.fenced_code import FencedCodeExtension
    from markdown.extensions.tables import TableExtension
except ImportError:
    print('Please install markdown')
    exit(1)

try:
    import zstandard
except ImportError:
    print('Please install zstandard')
    exit(1)

# ── Global config ────────────────────────────────────────────────────────────
config = None


def _make_md():
    return markdown.Markdown(extensions=[
        FencedCodeExtension(),
        TableExtension(),
    ])


# ── Slug utilities ─────────────────────────────────────────────────────────
def slug_basename(slug):
    """Extract the filename part from a possibly prefixed slug (e.g. 'core/entity' → 'entity')."""
    normalized = str(slug).replace("\\", "/").strip("/")
    if not normalized:
        return ""
    return normalized.rsplit("/", 1)[-1]


def _normalize_slug(slug):
    """Normalize slugs to forward-slash format for cross-platform consistency."""
    return str(slug).replace("\\", "/").strip("/")


def _build_slug_page_keys(slugs):
    """Build unique output keys for slugs, disambiguating basename collisions."""
    groups = {}
    for slug in slugs:
        norm = _normalize_slug(slug)
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


def slug_page_key(slug):
    """Return the stable output key for a slug."""
    norm = _normalize_slug(slug)
    return config.get("_slug_page_keys", {}).get(norm, slug_basename(norm))


def slug_output_name(slug):
    """Return output HTML filename for a slug."""
    key = slug_page_key(slug)
    return "index.html" if key == "index" else f"{key}.html"


def get_all_slugs():
    """Get all markdown file slugs from the sidebar definition."""
    slugs = []
    for _, pages in sidebar(config):
        slugs.extend(slug for slug, _ in pages)

    return slugs


# ── Frontmatter parser ──────────────────────────────────────────────────────
def parse_frontmatter(text):
    """Extract YAML-like frontmatter and return (metadata_dict, remaining_text)."""
    if not text.startswith("---"):
        return {}, text

    end = text.find("---", 3)
    if end == -1:
        return {}, text

    fm_block = text[3:end].strip()
    body = text[end + 3:].strip()
    meta = {}
    for line in fm_block.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip()] = val.strip()

    return meta, body


def _get_logo_text(config):
    """Extract logo text from project_name (e.g., 'PyJavaBridge' → 'Py')."""
    name = project_name(config)
    if name:
        return name[0]
    return "Py"


def _get_copyright_year():
    import datetime
    return datetime.datetime.now().year


def _get_copyright_holder(config):
    """Extract copyright holder from project_name (e.g., 'PyJavaBridge' → 'Omena0')."""
    if "Omena0" in project_name(config):
        return "Omena0"
    return project_name(config)


def _build_extra_nav_links():
    return ""


def _render_template_placeholders(config):
    return {
        "site_prefix": config.get("_output_site_prefix", ""),
        "page_title": "",
        "project_name": project_name(config),
        "og_title": "",
        "og_description": "",
        "logo_text": _get_logo_text(config),
        "version_options": "",
        "extra_nav_links": _build_extra_nav_links(),
        "sidebar": "",
        "subtitle_html": "",
        "body": "",
        "search_index_inline": "",
        "copyright_year": _get_copyright_year(),
        "copyright_holder": _get_copyright_holder(config),
    }


def _safe_replace(text):
    return text.replace('{', '{{').replace('}', '}}') if isinstance(text, str) else text


def _make_md():
    return markdown.Markdown(extensions=[
        FencedCodeExtension(),
        TableExtension(),
    ])


# ── Synta


def highlight_python(code):
    """Highlight Python-like tokens using the precompiled regex."""
    # Precompile tokens once for performance
    PYTHON_KEYWORDS = {
        'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
        'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
        'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
        'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try',
        'while', 'with', 'yield',
    }

    TOKEN_SPECS = [
        ('st', r'&quot;&quot;&quot;.*?&quot;&quot;&quot;|&#x27;&#x27;&#x27;.*?&#x27;&#x27;&#x27;'),
        ('st', r'f?&quot;(?:[^&]|&(?!quot;))*?&quot;|f?&#x27;(?:[^&]|&(?!#x27;))*?&#x27;'),
        ('cm', r'#[^\n]*'),
        ('dc', r'@\w+'),
        ('nb', r'\b\d+\.?\d*\b'),
        ('kw', r'\b(?:' + '|'.join(sorted(PYTHON_KEYWORDS, key=len, reverse=True)) + r')\b'),
    ]

    HIGHLIGHT_CLASSES = [cls for cls, _ in TOKEN_SPECS]
    HIGHLIGHT_PATTERN = '|'.join(f'(?P<g{i}>{pat})' for i, (_, pat) in enumerate(TOKEN_SPECS))
    HIGHLIGHT_RE = re.compile(HIGHLIGHT_PATTERN, flags=re.DOTALL)

    def _replacer(m):
        for i, cls in enumerate(HIGHLIGHT_CLASSES):
            if m.group(f'g{i}') is not None:
                return f'<span class="{cls}">{m.group(f"g{i}")}</span>'
        return m.group(0)

    return HIGHLIGHT_RE.sub(_replacer, code)


def highlight_code_blocks(html_text):
    """Apply highlighting to <pre><code class=\"language-...\"> blocks."""
    def replace_block(m):
        lang = m.group(1) or ""
        inner = m.group(2)
        if "python" in lang or "py" in lang:
            inner = highlight_python(inner)
        return f'<pre><code class="language-{lang}">{inner}</code></pre>'

    return PRE_CODE_RE.sub(replace_block, html_text)


# Initialize syntax highlighting patterns
PYTHON_KEYWORDS = {
    'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
    'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
    'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
    'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try',
    'while', 'with', 'yield',
}

TOKEN_SPECS = [
    ('st', r'&quot;&quot;&quot;.*?&quot;&quot;&quot;|&#x27;&#x27;&#x27;.*?&#x27;&#x27;&#x27;'),
    ('st', r'f?&quot;(?:[^&]|&(?!quot;))*?&quot;|f?&#x27;(?:[^&]|&(?!#x27;))*?&#x27;'),
    ('cm', r'#[^\n]*'),
    ('dc', r'@\w+'),
    ('nb', r'\b\d+\.?\d*\b'),
    ('kw', r'\b(?:' + '|'.join(sorted(PYTHON_KEYWORDS, key=len, reverse=True)) + r')\b'),
]

HIGHLIGHT_CLASSES = [cls for cls, _ in TOKEN_SPECS]
HIGHLIGHT_PATTERN = '|'.join(f'(?P<g{i}>{pat})' for i, (_, pat) in enumerate(TOKEN_SPECS))
HIGHLIGHT_RE = re.compile(HIGHLIGHT_PATTERN, flags=re.DOTALL)

PRE_CODE_RE = re.compile(r'<pre><code class="language-(\w*)">(.*?)</code></pre>', flags=re.DOTALL)
URL_ATTR_RE = re.compile(
    r'(?P<attr>\b(?:href|src))\s*=\s*(?P<quote>["\']?)(?P<url>[^"\'\s>]+)(?P=quote)',
    flags=re.IGNORECASE,
)

# ── Frontmatter parser ──────────────────────────────────────────────────────
def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}, text

    end = text.find("---", 3)
    if end == -1:
        return {}, text

    fm_block = text[3:end].strip()
    body = text[end + 3:].strip()
    meta = {}
    for line in fm_block.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip()] = val.strip()

    return meta, body


def process_blockquotes(html_text):
    def classify(m):
        content = m.group(1)
        if content.strip().startswith("<strong>Warning"):
            cls = "callout callout-warn"
        elif content.strip().startswith("<strong>Tip"):
            cls = "callout callout-tip"
        elif content.strip().startswith("<strong>Note"):
            cls = "callout callout-info"
        elif content.strip().startswith("<strong>See also"):
            cls = "callout callout-info"
        else:
            cls = "callout callout-info"

        return f'<div class="{cls}">{content}</div>'

    return re.sub(r'<blockquote>\s*(.*?)\s*</blockquote>', classify, html_text, flags=re.DOTALL)


def format_ext_tags(html_text):
    return html_text.replace('[ext]', '<span class="ext-tag">ext</span>')


# ── Markdown → HTML conversion ──────────────────────────────────────────────
_MD_LOCAL = threading.local()


def convert_markdown(text):
    """Convert markdown text to HTML using a per-thread Markdown instance."""
    md = getattr(_MD_LOCAL, 'md', None)
    if md is None:
        md = _make_md()
        _MD_LOCAL.md = md

    md.reset()
    html_out = md.convert(text)
    toc_tokens = getattr(md, 'toc_tokens', [])
    md.reset()
    return html_out, toc_tokens


def _resolve_md_target_to_output(md_target, current_slug):
    raw = str(md_target or "").strip()
    if not raw:
        return raw

    raw = raw.replace("\\", "/")
    candidates = []
    if raw.startswith("/"):
        candidates.append(posixpath.normpath(raw.lstrip("/")))
    else:
        candidates.append(posixpath.normpath(raw))
        base_dir = ""
        if current_slug:
            normalized_current = _normalize_slug(current_slug)
            base_dir = normalized_current.rsplit("/", 1)[0] if "/" in normalized_current else ""
        candidates.append(posixpath.normpath(posixpath.join(base_dir, raw)))

    for candidate in candidates:
        normalized = _normalize_slug(candidate)
        if normalized in config.get("_slug_page_keys", {}):
            return slug_output_name(normalized)

    return f"{raw}.html"


def rewrite_md_links(html_text, current_slug):
    def _repl(m):
        target = m.group(1)
        anchor = m.group(2) or ""
        resolved = _resolve_md_target_to_output(target, current_slug)
        return f'href="{resolved}{anchor}"'

    return re.sub(r'href="([^"]+)\.md(#[^"]*)?"', _repl, html_text)


def _normalized_site_prefix():
    prefix = config.get("site_path_prefix", "").strip()
    if not prefix:
        return "/"
    if not prefix.startswith("/"):
        prefix = "/" + prefix
    if not prefix.endswith("/"):
        prefix += "/"
    return prefix


def _output_site_prefix():
    return _normalized_site_prefix() if config.get("production", False) else ""


def _output_href(path):
    clean = str(path or "").lstrip("/")
    prefix = _output_site_prefix()
    if not prefix:
        return clean
    return prefix + clean


def _should_absolutize_url(raw_url):
    if not raw_url:
        return False
    value = raw_url.strip()
    if not value or value.startswith("#") or value.startswith("//"):
        return False
    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', value):
        return False
    return True


def absolutize_links(html_text, page_url):
    if not html_text or not page_url:
        return html_text

    prefix = _normalized_site_prefix().rstrip("/") or "/"

    def _repl(m):
        attr = m.group("attr")
        quote = m.group("quote")
        raw_url = m.group("url")
        if not _should_absolutize_url(raw_url):
            return m.group(0)
        resolved = urljoin(page_url, raw_url)
        parts = urlsplit(resolved)
        absolute = parts.path or "/"
        if prefix != "/" and absolute.startswith("/") and absolute != prefix and not absolute.startswith(prefix + "/"):
            absolute = prefix + absolute
        if parts.query:
            absolute += f"?{parts.query}"
        if parts.fragment:
            absolute += f"#{parts.fragment}"
        if quote:
            return f"{attr}={quote}{absolute}{quote}"
        return f"{attr}={absolute}"

    return URL_ATTR_RE.sub(_repl, html_text)


def auto_link_markdown(md_text, search_map):
    """Auto-link plain class names in Markdown to their docs using search_map."""
    if not search_map:
        return md_text

    code_fence_pat = re.compile(r'```[\s\S]*?```')
    code_fences = []

    def _cf(m):
        code_fences.append(m.group(0))
        return f"@@CODEFENCE{len(code_fences)-1}@@"

    text = code_fence_pat.sub(_cf, md_text)

    inline_code_pat = re.compile(r'`([^`]*?)`')
    inline_codes = []

    def _ic(m):
        inline_codes.append(m.group(1))
        return f"@@INLINECODE{len(inline_codes)-1}@@"

    text = inline_code_pat.sub(_ic, text)

    link_pat = re.compile(r'\[[^\]]+\]\([^\)]+\)')
    links = []

    def _ln(m):
        links.append(m.group(0))
        return f"@@LINK{len(links)-1}@@"

    text = link_pat.sub(_ln, text)

    def _transform_inline_content(content):
        esc = html.escape(content)
        if 'SEARCH_RE' in globals() and SEARCH_RE:
            def _linker(m):
                k = m.group(1)
                dest = search_map.get(k)
                return f'<a href="{dest}">{k}</a>' if dest else k

            esc = SEARCH_RE.sub(_linker, esc)
        else:
            for name in sorted(search_map.keys(), key=len, reverse=True):
                dest = search_map[name]
                pattern = r'(?<![A-Za-z0-9_])' + re.escape(name) + r'(?![A-Za-z0-9_])'
                esc = re.sub(pattern, f'<a href="{dest}">{name}</a>', esc)

        def _decor_replace(m):
            nm = m.group(1)
            return f'<a href="{DECORATORS_DEST}#{nm}">@{nm}</a>'

        esc = re.sub(r'@([A-Za-z_][A-Za-z0-9_]*)', _decor_replace, esc)

        esc = esc.replace('[', '&#91;').replace(']', '&#93;')

        return f'<code>{esc}</code>'

    transformed_inlines = [_transform_inline_content(c) for c in inline_codes]

    def _restore_link(m):
        return links[int(m.group(1))]

    text = re.sub(r'@@LINK(\d+)@@', _restore_link, text)

    def _restore_inline(m):
        return transformed_inlines[int(m.group(1))]

    text = re.sub(r'@@INLINECODE(\d+)@@', _restore_inline, text)

    text = re.sub(r'@@CODEFENCE(\d+)@@', lambda m: code_fences[int(m.group(1))], text)

    return text


def _determine_ext_sections(config):
    """Determine which sections should have the [ext] tag."""
    sidebar_config = sidebar(config)
    ext_sections = []
    for section_name, _ in sidebar_config:
        if "[ext]" in section_name:
            ext_sections.append(section_name)
    return ext_sections if ext_sections else {"Extensions"}


def build_page(slug):
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

    try:
        if config.get("search_map"):
            body_md = auto_link_markdown(body_md, config["search_map"])
    except Exception:
        pass

    body_html, toc_tokens = convert_markdown(body_md)
    body_html = rewrite_md_links(body_html, slug)
    body_html = highlight_code_blocks(body_html)
    body_html = process_blockquotes(body_html)
    body_html = format_ext_tags(body_html)

    subtitle_html = f'<p class="subtitle">{subtitle}</p>' if subtitle else ""

    ext_sections = _determine_ext_sections(config)
    sidebar_html = build_toc_sidebar(toc_tokens, slug, sidebar(config), ext_sections)

    og_description = subtitle or f"{title} — {project_name(config)} documentation"

    placeholders = _render_template_placeholders(config)
    placeholders.update({
        "page_title": page_title,
        "og_title": og_title,
        "og_description": og_description,
        "subtitle_html": subtitle_html,
        "sidebar": sidebar_html,
        "body": body_html,
    })

    out_html = TEMPLATE.format(**placeholders)

    try:
        out_html = optimize_html(out_html)
    except Exception as e:
        print(f'Failed to optimize HTML: {e}')

    try:
        out_html = minify_html(out_html)
    except Exception as e:
        print(f'Failed to minify HTML: {e}')

    if config.get("production", False):
        resolver_base = urljoin("https://docs.local", _normalized_site_prefix())
        page_url = urljoin(resolver_base, slug_output_name(slug))
        out_html = absolutize_links(out_html, page_url)

    out_name = slug_output_name(slug)
    out_path = os.path.join(config["_out_dir"], out_name)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out_html)


def optimize_html(html_input, base_path=None):
    if not cfg_optimize_html(config):
        return html_input

    with tempfile.NamedTemporaryFile("w+", suffix=".html", delete=False) as f_in:
        f_in.write(html_input)
        in_path = Path(f_in.name)

    if base_path is None:
        base_path = config["_out_dir"]
    elif not os.path.isabs(base_path):
        base_path = os.path.join(config["_docs_dir"], base_path)

    cmd = [
        "npx", "critical",
        str(in_path),
        "--base", str(base_path),
        "--inline",
        "--extract",
        "--width", "1920",
        "--height", "1080",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

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
        except:
            pass


def minify_html(html_input):
    if not cfg_minify_html(config):
        return html_input

    with tempfile.NamedTemporaryFile("w+", suffix=".html", delete=False) as temp_in:
        temp_in.write(html_input)
        temp_in_path = Path(temp_in.name)

    with tempfile.NamedTemporaryFile("r+", suffix=".html", delete=False) as temp_out:
        temp_out_path = Path(temp_out.name)

    cmd = [
        "npx", "html-minifier-next",
        "--minify-css", "true",
        "--minify-js", "true",
        "--minify-svg", "true",
        "--minify-urls", "true",
        "--remove-attribute-quotes",
        "--collapse-whitespace",
        "--remove-tag-whitespace",
        "--remove-comments",
        "-o", str(temp_out_path),
        str(temp_in_path)
    ]

    subprocess.run(cmd, check=True)

    minified_html = temp_out_path.read_text(encoding="utf-8")

    temp_in_path.unlink()
    temp_out_path.unlink()

    return minified_html


def main(argv=None):
    global config
    # Normalize: if argv starts with "build", strip it
    if argv is not None and argv and argv[0] == "build":
        argv = argv[1:]
    elif argv is None:
        # When called directly from entry point, sys.argv will contain "build"
        import sys
        from pathlib import Path
        if Path(sys.argv[0]).name == "fr-docs" and len(sys.argv) > 1 and sys.argv[1] == "build":
            # Remove "build" from sys.argv before parsing
            sys.argv.pop(1)
            argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Build the fr-docs documentation site.")
    parser.add_argument(
        "--production",
        action="store_true",
        help="Rewrite internal links to site-root absolute paths for deployed docs.",
    )
    parser.add_argument(
        "--config",
        help="Path to the configuration JSON file.",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    config["production"] = bool(args.production)

    print(f"📖 Building {project_name(config)} docs...")
    print(f"   Source: {src_dir(config)}")
    print(f"   Output: {out_dir(config)}")
    print(f"   Mode: {'production' if args.production else 'development'}")
    if args.production:
        print(f"   Site prefix: {_normalized_site_prefix()}")
    print()

    # Copy static assets
    docs_path = Path(config["_docs_dir"])
    for name in ('favicon.svg', 'script.js', 'style.css'):
        src = docs_path / name
        dst = Path(config["_out_dir"]) / name

        try:
            shutil.copyfile(src, dst)
        except Exception:
            print(f"   ⚠ Could not copy {name} (source {src} missing)")

    slugs = get_all_slugs()

    # Also check for any .md files not in the sidebar
    if os.path.isdir(config["_src_dir"]):
        for dirpath, _dirnames, filenames in os.walk(config["_src_dir"]):
            for fname in filenames:
                if fname.endswith(".md"):
                    rel = os.path.relpath(os.path.join(dirpath, fname), config["_src_dir"])
                    s = rel[:-3]
                    if s not in slugs:
                        slugs.append(s)

    config["_slug_page_keys"] = _build_slug_page_keys(slugs)

    built = 0
    search_index = []

    # Build search index
    for slug in slugs:
        src = os.path.join(config["_src_dir"], f"{slug}.md")

        if os.path.exists(src):
            with open(src, "r", encoding="utf-8") as f:
                raw = f.read()

            meta, body_md = parse_frontmatter(raw)

            title = meta.get("title", slug.capitalize())
            current_heading = title

            sections = []
            in_table = False

            table_first_cols = []
            table_header_seen = False

            for line in body_md.split("\n"):
                stripped = line.strip()

                if stripped.startswith("|") and "|" in stripped[1:]:
                    if re.match(r'^\|[\s\-:|]+\|$', stripped):
                        table_header_seen = True
                        continue

                    if not in_table:
                        in_table = True
                        table_header_seen = False
                        continue

                    if not table_header_seen:
                        continue

                    cols = [c.strip() for c in stripped.strip("|").split("|")]

                    if cols:
                        col = re.sub(r'[`*\[\]()]', '', cols[0]).strip()

                        if col:
                            table_first_cols.append(col)

                    continue

                else:
                    if in_table and table_first_cols:
                        sections.append({"heading": current_heading, "text": ", ".join(table_first_cols)})
                        table_first_cols = []

                    in_table = False
                    table_header_seen = False

                if stripped.startswith("#"):
                    current_heading = stripped.lstrip("#").strip()

                elif stripped and not stripped.startswith("```") and not stripped.startswith("---"):
                    clean = re.sub(r'[`*\[\]()]', '', stripped)

                    if clean:
                        sections.append({"heading": current_heading, "text": clean})

            if table_first_cols:
                sections.append({"heading": current_heading, "text": ", ".join(table_first_cols)})

            page_key = slug_page_key(slug)
            url = _output_href(slug_output_name(slug))
            search_index.append({
                "slug": page_key,
                "source_slug": _normalize_slug(slug),
                "title": title,
                "url": url,
                "sections": sections,
            })

    # Build search map
    config["search_map"] = {}
    for item in search_index:
        title = item.get('title') or ''
        source_slug = item.get('source_slug') or item.get('slug')
        if not title or not source_slug:
            continue

        cleaned = re.sub(r'\[ext\]', '', title)
        cleaned = re.sub(r'[`*()]+', '', cleaned).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)

        config["search_map"][cleaned] = f"{source_slug}.md"
        if title != cleaned:
            config["search_map"][title] = f"{source_slug}.md"

    # Compile search regex
    SEARCH_RE = None
    try:
        keys = sorted(config["search_map"].keys(), key=len, reverse=True)
        if keys:
            SEARCH_RE = re.compile(r'(?<![A-Za-z0-9_])(' + '|'.join(re.escape(k) for k in keys) + r')(?![A-Za-z0-9_])')
    except Exception:
        SEARCH_RE = None

    DECORATORS_DEST = config["search_map"].get('Decorators') or config["search_map"].get('decorators') or 'decorators.md'

    # Backlinks and related pages
    title_to_slug = {item['title'].lower(): item['slug'] for item in search_index}

    page_texts = {}
    for item in search_index:
        combined = item.get('title', '') + ' '
        for s in item.get('sections', []):
            combined += ' ' + (s.get('heading', '') or '') + ' ' + (s.get('text', '') or '')
        page_texts[item['slug']] = re.sub(r'\s+', ' ', combined).lower()

    slug_to_backlinks = {item['slug']: [] for item in search_index}
    for src in search_index:
        src_text = page_texts[src['slug']]
        for tgt in search_index:
            if src['slug'] == tgt['slug']:
                continue
            ttitle = (tgt.get('title') or '').lower()
            if not ttitle:
                continue
            if ttitle in src_text:
                slug_to_backlinks[tgt['slug']].append(src['slug'])

    def words(s):
        return set(re.findall(r"[a-z0-9]{3,}", s.lower()))

    word_sets = {slug: words(text) for slug, text in page_texts.items()}
    related_map = {}
    for a in page_texts:
        scores = []
        for b in page_texts:
            if a == b:
                continue
            inter = len(word_sets[a].intersection(word_sets[b]))
            if inter > 0:
                scores.append((inter, b))
        scores.sort(reverse=True)
        related_map[a] = [b for _, b in scores[:6]]

    for item in search_index:
        item['backlinks'] = slug_to_backlinks.get(item['slug'], [])
        item['related'] = related_map.get(item['slug'], [])

    # Git metadata (simplified - only repo name and commits for basic functionality)
    git_meta = {'repo': None, 'commits': [], 'tags': {}, 'versions': [], 'src_map': {}, 'pages_by_commit': {}}
    try:
        repo_root = Path(config["_docs_dir"]).parent
        try:
            remote_url = subprocess.check_output(['git', 'remote', 'get-url', 'origin'], cwd=repo_root, text=True).strip()
        except Exception:
            remote_url = ''

        repo_name = None
        m = re.search(r'github.com[:/](.+?)(?:\.git)?$', remote_url)
        if m:
            repo_name = m.group(1)

        try:
            log_out = subprocess.check_output(['git', 'log', '--pretty=format:%H%x01%s', '--reverse'], cwd=repo_root, text=True)
            for line in log_out.splitlines():
                if not line:
                    continue
                parts = line.split('\x01', 1)
                if len(parts) == 2:
                    h, msg = parts
                else:
                    h = parts[0]; msg = ''
                git_meta['commits'].append(h)
                m = re.match(r"^\s*([0-9]+[A-Za-z])\s*[-:—–]\s*(.+)", msg)
                if m:
                    code = m.group(1).upper()
                    label = m.group(2).strip()
                    git_meta['versions'].append({'code': code, 'commit': h, 'label': label})
        except Exception:
            pass

        # Build src_map for historical markdown fetching
        for slug in slugs:
            git_meta['src_map'][slug_page_key(slug)] = src_map_path(config)

    except Exception:
        pass

    try:
        with open(os.path.join(config["_out_dir"], git_meta_filename(config)), 'w', encoding='utf-8') as gf:
            json.dump(git_meta, gf, separators=(',', ':'))
    except Exception:
        pass

    # Pre-render version selector options
    try:
        opts = [f'<option value="">{live_label(config)}</option>']
        if git_meta['versions']:
            for v in reversed(git_meta['versions']):
                code = v.get('code')
                commit = v.get('commit', '')
                label = v.get('label', '')
                if not code:
                    continue
                esc_code = html.escape(code)
                if label:
                    esc_label = html.escape(label)
                    esc_commit = html.escape(commit[:8])
                    opts.append(f'<option value="{esc_code}" data-label="{esc_label}" data-commit="{esc_commit}">{esc_code}</option>')
                else:
                    esc_commit = html.escape(commit[:8])
                    opts.append(f'<option value="{esc_code}" data-commit="{esc_commit}">{esc_code}</option>')
        else:
            if git_meta['commits']:
                latest = git_meta['commits'][-1]
                esc_commit = html.escape(latest[:8])
                opts.append(f'<option value="{latest}" data-commit="{esc_commit}">{esc_commit}</option>')

        config["_version_options"] = '\n'.join(opts)
    except Exception:
        config["_version_options"] = f'<option value="">{live_label(config)}</option>'

    # Build search index file
    import json
    search_json = json.dumps(search_index, separators=(',', ':'))
    cctx = zstandard.ZstdCompressor(level=zstd_level(config))

    compressed = cctx.compress(search_json.encode('utf-8'))
    search_index_path = os.path.join(config["_out_dir"], search_index_filename(config))
    os.makedirs(os.path.dirname(search_index_path), exist_ok=True)
    with open(search_index_path, "wb") as sf:
        sf.write(compressed)

    if args.production:
        config["_search_index_inline"] = ""
    else:
        config["_search_index_inline"] = (
            '<script id="zstd-data" type="text/plain">'
            f'{base64.b64encode(compressed).decode("ascii")}'
            '</script>'
        )

    print(f"   Search index: {len(search_json.encode('utf-8')):,} bytes → {len(compressed):,} zstd ({100*len(compressed)/len(search_json.encode('utf-8')):.1f}%)")

    # Build pages
    slugs_to_build = []
    for slug in slugs:
        src = os.path.join(config["_src_dir"], f"{slug}.md")
        if os.path.exists(src):
            slugs_to_build.append(slug)

    if slugs_to_build:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers(config)) as executor:
            future_to_slug = {executor.submit(build_page, slug): slug for slug in slugs_to_build}
            for fut in concurrent.futures.as_completed(future_to_slug):
                slug = future_to_slug[fut]
                try:
                    fut.result()
                    print(f"  ✓ {slug_output_name(slug)}")
                    built += 1
                except Exception as e:
                    print(f"  ✗ {slug_output_name(slug)} (error: {e})")
    else:
        print("No pages found to build.")

    print(f"\n✅ Built {built} pages")


def _normalized_site_prefix():
    prefix = config.get("site_path_prefix", "").strip()
    if not prefix:
        return "/"
    if not prefix.startswith("/"):
        prefix = "/" + prefix
    if not prefix.endswith("/"):
        prefix += "/"
    return prefix


def _output_site_prefix():
    return _normalized_site_prefix() if config.get("production", False) else ""


def _output_href(path):
    clean = str(path or "").lstrip("/")
    prefix = _output_site_prefix()
    if not prefix:
        return clean
    return prefix + clean


if __name__ == "__main__":
    main()
