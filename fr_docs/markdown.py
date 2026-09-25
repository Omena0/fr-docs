"""Markdown conversion and link handling for fr-docs."""

import html
import re
import threading
from urllib.parse import urljoin, urlsplit

import markdown
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension

from .slug import (
    normalize_slug,
    slug_output_name,
)
from .syntax import URL_ATTR_RE

_DECORATORS_DEST = "decorators"

_MD_LOCAL = threading.local()

# Pattern to match code reference links: [text](path/to/file.py:123) or [text](path/to/file.py)
# Only matches source code files, not markdown/documentation files
CODE_REF_RE = re.compile(
    r"\[([^\]]+)\]\(([a-zA-Z0-9_./\\-]+\.(?:py|js|ts|tsx|jsx|java|cpp|c|h|hpp|rs|go|rb|php|cs|kt|swift|scala|clj|hs|ml|fs|vim|sh|bash|zsh|fish|ps1|bat|cmd|sql|html|htm|xml|json|yaml|yml|toml|ini|cfg|conf|css|scss|sass|less|styl|vue|svelte|astro|mdx))(?::(\d+))?\)"
)


def _make_md():
    return markdown.Markdown(
        extensions=[
            FencedCodeExtension(),
            TableExtension(),
        ]
    )


def convert_markdown(text):
    """Convert markdown text to HTML using a per-thread Markdown instance."""
    md = getattr(_MD_LOCAL, "md", None)
    if md is None:
        md = _make_md()
        _MD_LOCAL.md = md

    md.reset()
    html_out = md.convert(text)
    toc_tokens = getattr(md, "toc_tokens", [])
    md.reset()
    return html_out, toc_tokens


def resolve_md_target(md_target, current_slug, slug_page_keys):
    """Resolve a markdown link target to an output HTML filename."""
    raw = str(md_target or "").strip()
    if not raw:
        return raw

    raw = raw.replace("\\", "/")
    raw = re.sub(r"\.(?:md|html)$", "", raw)

    candidates = []
    if raw.startswith("/"):
        candidates.append(normalize_slug(raw.lstrip("/")))
    else:
        candidates.append(normalize_slug(raw))
        base_dir = ""
        if current_slug:
            normalized_current = normalize_slug(current_slug)
            base_dir = (
                normalized_current.rsplit("/", 1)[0]
                if "/" in normalized_current
                else ""
            )
        candidates.append(normalize_slug(f"{base_dir}/{raw}" if base_dir else raw))

    for candidate in candidates:
        if candidate in slug_page_keys:
            return slug_output_name(candidate)

    return slug_output_name(normalize_slug(raw))


def rewrite_md_links(html_text, current_slug, slug_page_keys):
    """Rewrite internal .md links to output HTML filenames."""

    def _repl(m):
        # Match both double and single quotes
        quote = m.group(1)
        target = m.group(2)
        anchor = m.group(3) or ""
        resolved = resolve_md_target(target, current_slug, slug_page_keys)
        return f'href={quote}{resolved}{anchor}{quote}'

    # Match href="target.md#anchor" or href='target.md#anchor'
    # Also handle query parameters: href="target.md?param=value#anchor"
    return re.sub(r'href=(["\'])([^"\']+?\.md)(\?[^"\']*?)?(#[^"\']*)?\1', _repl, html_text)


def should_absolutize_url(raw_url):
    if not raw_url:
        return False
    value = raw_url.strip()
    if not value or value.startswith(("#", "//")):
        return False
    return not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", value)


def absolutize_links(html_text, page_url, site_prefix):
    if not html_text or not page_url:
        return html_text

    prefix = site_prefix.rstrip("/") or "/"

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


def process_code_references(md_text, config):
    """Process code reference links in markdown: [text](path/to/file.py:123).

    NOTE: This is kept for backwards compatibility but does nothing.
    Code references are now processed in HTML after markdown conversion
    via process_code_references_html() to avoid HTML escaping issues.

    Returns tuple of (processed_text, code_refs).
    """
    if not config.get("features", {}).get("code_references", True):
        return md_text, []

    # Just return the original text - we'll process in HTML stage
    return md_text, []


def process_code_references_html(html_text, config):
    """Process code reference links in HTML: [text](path/to/file.py:123).

    Only processes references INSIDE <pre><code> blocks.
    Returns tuple of (processed_html, code_refs).
    """
    if not config.get("features", {}).get("code_references", True):
        return html_text, []

    # Pattern to match <pre><code> blocks
    pre_code_pat = re.compile(r'(<pre><code[^>]*>[\s\S]*?</code></pre>)')

    code_refs = []
    ref_counter = 0
    processed_parts = []
    last_end = 0

    for match in pre_code_pat.finditer(html_text):
        # Add text before the code block
        processed_parts.append(html_text[last_end:match.start()])

        # Process the code block
        code_block = match.group(1)
        processed_block, block_refs = _process_code_refs_in_html_block(code_block, ref_counter)
        code_refs.extend(block_refs)
        ref_counter += len(block_refs)
        processed_parts.append(processed_block)

        last_end = match.end()

    # Add remaining text
    processed_parts.append(html_text[last_end:])

    return "".join(processed_parts), code_refs


def _process_code_refs_in_html_block(block_html, start_counter):
    """Process code references inside a single <pre><code> block."""
    code_refs = []
    ref_counter = start_counter

    def _repl(m):
        nonlocal ref_counter
        link_text = m.group(1)
        file_path = m.group(2)
        line_str = m.group(3)
        line = int(line_str) if line_str else None

        ref_id = f"coderef-{ref_counter}"
        ref_counter += 1

        code_refs.append(
            {
                "id": ref_id,
                "file": file_path,
                "line": line,
                "column": None,
                "link_text": link_text,
            }
        )

        return f'<a href="#coderef-{ref_id}" class="code-reference" data-coderef-id="{ref_id}" data-coderef-file="{html.escape(file_path, quote=True)}" data-coderef-line="{line if line else ""}">{html.escape(link_text)}</a>'

    processed = CODE_REF_RE.sub(_repl, block_html)
    return processed, code_refs


def auto_link_markdown(md_text, search_map):
    """Auto-link plain class names in Markdown to their docs using search_map."""
    if not search_map:
        return md_text

    code_fence_pat = re.compile(r"```[\s\S]*?```")
    code_fences = []

    def _cf(m):
        code_fences.append(m.group(0))
        return f"@@CODEFENCE{len(code_fences) - 1}@@"

    text = code_fence_pat.sub(_cf, md_text)

    inline_code_pat = re.compile(r"`([^`]*?)`")
    inline_codes = []

    def _ic(m):
        inline_codes.append(m.group(1))
        return f"@@INLINECODE{len(inline_codes) - 1}@@"

    text = inline_code_pat.sub(_ic, text)

    link_pat = re.compile(r"\[[^\]]+\]\([^\)]+\)")
    links = []

    def _ln(m):
        links.append(m.group(0))
        return f"@@LINK{len(links) - 1}@@"

    text = link_pat.sub(_ln, text)

    def _transform_inline_content(content):
        # Just escape and wrap in <code> - don't auto-link inside inline code
        esc = html.escape(content)
        esc = esc.replace("[", "&#91;").replace("]", "&#93;")
        return f"<code>{esc}</code>"

    transformed_inlines = [_transform_inline_content(c) for c in inline_codes]

    def _restore_link(m):
        return links[int(m.group(1))]

    text = re.sub(r"@@LINK(\d+)@@", _restore_link, text)

    def _restore_inline(m):
        return transformed_inlines[int(m.group(1))]

    text = re.sub(r"@@INLINECODE(\d+)@@", _restore_inline, text)

    text = re.sub(r"@@CODEFENCE(\d+)@@", lambda m: code_fences[int(m.group(1))], text)

    return text
