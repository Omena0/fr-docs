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

CODE_REF_TARGET = r"(?::(?P<location>[^)]+))?"
CODE_REF_RE = re.compile(
    r"\[(?P<link_text>[^\]]+)\]\((?P<file>[a-zA-Z0-9_./\\-]+\.(?:py|js|ts|tsx|jsx|java|cpp|c|h|hpp|rs|go|rb|php|cs|kt|swift|scala|clj|hs|ml|fs|vim|sh|bash|zsh|fish|ps1|bat|cmd|sql|xml|json|yaml|yml|toml|ini|cfg|conf|css|scss|sass|less|styl|vue|svelte|astro|mdx))"
    + CODE_REF_TARGET
    + r"\)",
    flags=re.IGNORECASE,
)
CODE_REF_HTML_RE = re.compile(
    r'<a\s+href=(["\'])(?P<file>[^"\']+\.(?:py|js|ts|tsx|jsx|java|cpp|c|h|rs|go|rb|php|cs|kt|swift|scala|clj|hs|ml|fs|sh|bash|zsh|fish|ps1|bat|cmd|sql|xml|json|yaml|yml|toml|ini|cfg|conf|css|scss|sass|less|styl|vue|svelte|astro|mdx))(?::(?P<location>[^"\']+))?\1[^>]*>(?P<link_text>.*?)</a>',
    flags=re.IGNORECASE,
)


def _parse_code_location(location):
    location = str(location or "").strip()
    if not location:
        return {}
    if re.fullmatch(r"\d+", location):
        return {"line": int(location)}
    range_match = re.fullmatch(r"(\d+)-(\d+)(?::\d+)?", location)
    if range_match:
        return {
            "line": int(range_match.group(1)),
            "end_line": int(range_match.group(2)),
        }
    column_match = re.fullmatch(r"(\d+):(\d+)", location)
    if column_match:
        return {
            "line": int(column_match.group(1)),
            "column": int(column_match.group(2)),
        }
    return {"function": location}


def _code_ref_data(file_path, location, link_text, ref_id):
    return {
        "id": ref_id,
        "file": file_path,
        "link_text": link_text,
        "column": None,
        "line": None,
        "end_line": None,
        "function": None,
        **_parse_code_location(location),
    }


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
        return f"href={quote}{resolved}{anchor}{quote}"

    # Match href="target.md#anchor" or href='target.md#anchor'
    # Also handle query parameters: href="target.md?param=value#anchor"
    return re.sub(
        r'href=(["\'])([^"\']+?\.md)(\?[^"\']*?)?(#[^"\']*)?\1', _repl, html_text
    )


def auto_link_filenames(html_text, current_slug, slug_page_keys):
    """Auto-link bare filename references like `config.json` to their .md pages.

    Only processes filenames INSIDE inline code tags (<code>...</code>).
    SKIPS multiline code blocks (<pre><code>...</code></pre>).
    """
    if not slug_page_keys:
        return html_text

    # Build a map of filename (without .md) -> output HTML file
    filename_map = {}
    for slug in slug_page_keys:
        filename = slug.rsplit("/", 1)[-1]
        if filename:
            output = slug_output_name(slug)
            filename_map[filename.lower()] = output
            filename_map[f"{filename}.md".lower()] = output

    if not filename_map:
        return html_text

    sorted_filenames = sorted(filename_map.keys(), key=len, reverse=True)
    escaped_filenames = [re.escape(fn) for fn in sorted_filenames]
    filename_pattern = "|".join(escaped_filenames)

    # First, protect <pre><code> blocks from processing
    pre_code_pattern = re.compile(
        r"(<pre><code[^>]*>.*?</code></pre>)", flags=re.DOTALL
    )
    pre_code_blocks = []

    def _protect_pre_code(m):
        pre_code_blocks.append(m.group(1))
        return f"@@PRECODE{len(pre_code_blocks) - 1}@@"

    protected_text = pre_code_pattern.sub(_protect_pre_code, html_text)

    # Now process inline <code> tags (but not <pre><code>)
    code_pattern = re.compile(r"(<code[^>]*>)(.*?)(</code>)", flags=re.DOTALL)

    def _process_code_block(m):
        before = m.group(1)
        content = m.group(2)
        after = m.group(3)

        pattern = f"(?<![a-zA-Z0-9_-])({filename_pattern}" + r")\b(?![a-zA-Z0-9_-])"

        def _repl(fn_match):
            matched = fn_match.group(1)
            target_slug = filename_map.get(matched.lower())
            if target_slug:
                return f'<a href="{target_slug}" class="filename-reference">{html.escape(matched)}</a>'
            return matched

        new_content = re.sub(pattern, _repl, content, flags=re.IGNORECASE)
        return before + new_content + after

    processed_text = code_pattern.sub(_process_code_block, protected_text)

    # Restore <pre><code> blocks
    def _restore_pre_code(m):
        return pre_code_blocks[int(m.group(1))]

    return re.sub(r"@@PRECODE(\d+)@@", _restore_pre_code, processed_text)


def strip_code_refs_outside_code_blocks(html_text):
    """Remove code reference links (file.py:line) that are OUTSIDE <pre><code> blocks.

    Code references should only work inside code blocks. Any [text](file.py:123)
    links created by markdown outside code blocks are converted to plain text.
    """
    # Protect <pre><code> blocks
    pre_code_pattern = re.compile(
        r"(<pre><code[^>]*>.*?</code></pre>)", flags=re.DOTALL
    )
    pre_code_blocks = []

    def _protect(m):
        pre_code_blocks.append(m.group(1))
        return f"@@PRECODE{len(pre_code_blocks) - 1}@@"

    protected = pre_code_pattern.sub(_protect, html_text)

    # Find <a> tags with href matching code reference pattern (file.py:line)
    # Pattern: href="something.py:123" or href='something.py:123'
    code_ref_link_pattern = re.compile(
        r'(<a\s+href=(["\'])([^"\']+\.(?:py|js|ts|tsx|jsx|java|cpp|c|h|rs|go|rb|php|cs|kt|swift|scala|clj|hs|ml|fs|sh|bash|zsh|fish|ps1|bat|cmd|sql|html|xml|json|yaml|yml|toml|ini|cfg|conf|md|txt|rst|css|scss|sass|less|styl|vue|svelte|astro|mdx):\d+)["\'][^>]*>)(.*?)(</a>)',
        flags=re.IGNORECASE,
    )

    def _repl(m):
        link_text = m.group(4)
        return f'<span class="code-reference-plain">{html.escape(link_text)}</span>'

    processed = code_ref_link_pattern.sub(_repl, protected)

    # Restore <pre><code> blocks
    def _restore(m):
        return pre_code_blocks[int(m.group(1))]

    return re.sub(r"@@PRECODE(\d+)@@", _restore, processed)


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

    Processes references both INSIDE and OUTSIDE <pre><code> blocks.
    Returns tuple of (processed_html, code_refs).
    """
    if not config.get("features", {}).get("code_references", True):
        return html_text, []

    code_refs = []
    ref_counter = [0]  # Use list for mutable counter in nested functions

    # First, protect <pre><code> blocks
    pre_code_pat = re.compile(r"(<pre><code[^>]*>[\s\S]*?</code></pre>)")
    pre_code_blocks = []

    def _protect(m):
        pre_code_blocks.append(m.group(1))
        return f"@@PRECODE{len(pre_code_blocks) - 1}@@"

    protected_html = pre_code_pat.sub(_protect, html_text)

    # Process code references OUTSIDE code blocks (regular <a> links)
    # Pattern: <a href="file.py:123">text</a>
    def _repl_outside(m):
        file_path = m.group("file")
        location = m.group("location")
        link_text = m.group("link_text")
        ref_id = f"coderef-{ref_counter[0]}"
        ref_counter[0] += 1
        ref = _code_ref_data(file_path, location, link_text, ref_id)
        code_refs.append(ref)
        line = ref.get("line") or ""
        end_line = ref.get("end_line") or ""
        function = ref.get("function") or ""
        column = ref.get("column") or ""
        return (
            f'<a href="#{ref_id}" class="code-reference" data-coderef-id="{ref_id}" '
            f'data-coderef-file="{html.escape(file_path, quote=True)}" '
            f'data-coderef-line="{line}" data-coderef-end-line="{end_line}" '
            f'data-coderef-column="{column}" data-coderef-function="{html.escape(function, quote=True)}">'
            f"{html.escape(link_text)}</a>"
        )

    processed = CODE_REF_HTML_RE.sub(_repl_outside, protected_html)

    # Now process code references INSIDE <pre><code> blocks
    def _restore_and_process(m):
        block_idx = int(m.group(1))
        block_html = pre_code_blocks[block_idx]
        processed_block, block_refs = _process_code_refs_in_html_block(
            block_html, ref_counter[0]
        )
        code_refs.extend(block_refs)
        ref_counter[0] += len(block_refs)
        return processed_block

    processed = re.sub(r"@@PRECODE(\d+)@@", _restore_and_process, processed)

    return processed, code_refs


def _process_code_refs_in_html_block(block_html, start_counter):
    """Process code references inside a single <pre><code> block."""
    code_refs = []
    ref_counter = start_counter

    def _repl(m):
        nonlocal ref_counter
        link_text = m.group("link_text")
        file_path = m.group("file")
        location = m.group("location")
        ref_id = f"coderef-{ref_counter}"
        ref_counter += 1
        ref = _code_ref_data(file_path, location, link_text, ref_id)
        code_refs.append(ref)
        line = ref.get("line") or ""
        end_line = ref.get("end_line") or ""
        function = ref.get("function") or ""
        column = ref.get("column") or ""
        return (
            f'<a href="#{ref_id}" class="code-reference" data-coderef-id="{ref_id}" '
            f'data-coderef-file="{html.escape(file_path, quote=True)}" '
            f'data-coderef-line="{line}" data-coderef-end-line="{end_line}" '
            f'data-coderef-column="{column}" data-coderef-function="{html.escape(function, quote=True)}">'
            f"{html.escape(link_text)}</a>"
        )

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
