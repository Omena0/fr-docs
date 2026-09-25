"""Syntax highlighting and HTML preprocessing for fr-docs."""

import html
import re

import fastpylight

PRE_CODE_RE = re.compile(
    r'<pre><code class="language-([\w+-]*)">(.*?)</code></pre>', flags=re.DOTALL
)
URL_ATTR_RE = re.compile(
    r'(?P<attr>\b(?:href|src))\s*=\s*(?P<quote>["\']?)(?P<url>[^"\'\s>]+)(?P=quote)',
    flags=re.IGNORECASE,
)
HTML_LINK_RE = re.compile(r"<a\b[^>]*>.*?</a>", flags=re.DOTALL)

LANGUAGE_ALIASES = {
    "": "plaintext",
    "c": "c",
    "cpp": "cpp",
    "cs": "csharp",
    "c++": "cpp",
    "h": "c",
    "htm": "html",
    "ini": "plaintext",
    "js": "javascript",
    "jsx": "jsx",
    "mjs": "javascript",
    "py": "python",
    "sh": "bash",
    "shell": "bash",
    "toml": "plaintext",
    "ts": "typescript",
    "yml": "yaml",
    "zsh": "zsh",
}


def normalize_language(language):
    """Return a language name supported by fastpylight."""
    name = (language or "").strip().lower()
    name = LANGUAGE_ALIASES.get(name, name)
    supported = fastpylight.languages()
    if name in supported:
        return name
    guessed = fastpylight.guess("", name)
    return guessed if guessed in supported else "plaintext"


def _highlight_fragment(code, language):
    """Highlight a raw code fragment and return the inner HTML."""
    normalized = normalize_language(language)
    try:
        highlighted = fastpylight.highlight_spans(code, normalized)
    except TypeError, ValueError:
        highlighted = fastpylight.highlight_spans(code, "plaintext")
    match = re.match(r"<pre><code>(.*)</code></pre>$", highlighted, flags=re.DOTALL)
    return match.group(1) if match else html.escape(code)


def _protect_html_links(code):
    links = []

    def replace(match):
        links.append(match.group(0))
        return f"___FRDOC_LINK_{len(links) - 1}___"

    return HTML_LINK_RE.sub(replace, code), links


def _restore_html_links(code, links):
    for index, link in enumerate(links):
        code = code.replace(f"___FRDOC_LINK_{index}___", link)
    return code


def highlight_code_blocks(html_text):
    """Apply fastpylight highlighting to fenced code blocks."""
    for_match = PRE_CODE_RE.pattern

    def replace_block(match):
        language = match.group(1) or ""
        inner = match.group(2)
        protected, links = _protect_html_links(inner)
        raw = html.unescape(protected)
        highlighted = _highlight_fragment(raw, language)
        highlighted = _restore_html_links(highlighted, links)
        return f'<pre><code class="language-{language}">{highlighted}</code></pre>'

    return re.sub(for_match, replace_block, html_text, flags=re.DOTALL)


def highlight_source_lines(content, file_path):
    """Return fastpylight-highlighted HTML lines for the source panel."""
    language = normalize_language(file_path.rsplit(".", 1)[-1])
    if language == "plaintext":
        return [html.escape(line) for line in content.splitlines()]
    highlighted = fastpylight.highlight_spans(content, language)
    match = re.match(r"<pre><code>(.*)</code></pre>$", highlighted, flags=re.DOTALL)
    if not match:
        return [html.escape(line) for line in content.splitlines()]
    return match.group(1).splitlines()


def process_blockquotes(html_text):
    def classify(m):
        content = m.group(1)
        if content.strip().startswith("<strong>Warning"):
            cls = "callout callout-warn"
        elif content.strip().startswith("<strong>Tip"):
            cls = "callout callout-tip"
        else:
            cls = "callout callout-info"
        return f'<div class="{cls}">{content}</div>'

    return re.sub(
        r"<blockquote>\s*(.*?)\s*</blockquote>", classify, html_text, flags=re.DOTALL
    )


def format_ext_tags(html_text):
    return html_text.replace("[ext]", '<span class="ext-tag">ext</span>')
