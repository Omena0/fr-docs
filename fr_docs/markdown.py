"""Markdown conversion and link handling for fr-docs."""

import html
import re
import threading
from urllib.parse import urljoin, urlsplit

import markdown
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension

from .slug import (
    slug_output_name,
    slug_page_key,
    normalize_slug,
    slug_basename,
)
from .syntax import URL_ATTR_RE

_DECORATORS_DEST = "decorators"

_MD_LOCAL = threading.local()


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
        candidates.append(
            normalize_slug(
                f"{base_dir}/{raw}" if base_dir else raw
            )
        )

    for candidate in candidates:
        if candidate in slug_page_keys:
            return slug_output_name(candidate)

    return slug_output_name(normalize_slug(raw))


def rewrite_md_links(html_text, current_slug, slug_page_keys):
    """Rewrite internal .md links to output HTML filenames."""

    def _repl(m):
        target = m.group(1)
        anchor = m.group(2) or ""
        resolved = resolve_md_target(target, current_slug, slug_page_keys)
        return f'href="{resolved}{anchor}"'

    return re.sub(r'href="([^"]+)\.md(#[^"]*)?"', _repl, html_text)


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
        esc = html.escape(content)
        for name in sorted(search_map.keys(), key=len, reverse=True):
            dest = search_map[name]
            pattern = r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])"
            esc = re.sub(pattern, f'<a href="{dest}">{name}</a>', esc)

        def _decor_replace(m):
            nm = m.group(1)
            return f'<a href="{_DECORATORS_DEST}#{nm}">@{nm}</a>'

        esc = re.sub(r"@([A-Za-z_][A-Za-z0-9_]*)", _decor_replace, esc)

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