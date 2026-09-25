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
    return [_highlight_fragment(line, language) for line in content.splitlines()]


CALLOUT_ICONS = {
    "note": '<svg viewBox="0 0 24 24"><path d="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 4v6m0 4h.01"/></svg>',
    "info": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 11v5m0-8h.01"/></svg>',
    "tip": '<svg viewBox="0 0 24 24"><path d="M9 18h6m-5 3h4M8 14a6 6 0 1 1 8 0c-.8.6-1 1.3-1 2H9c0-.7-.2-1.4-1-2Z"/></svg>',
    "warning": '<svg viewBox="0 0 24 24"><path d="m12 3 9 17H3L12 3Z"/><path d="M12 9v4m0 4h.01"/></svg>',
    "error": '<svg viewBox="0 0 24 24"><path d="m12 3 9 9-9 9-9-9 9-9Z"/><path d="m9 9 6 6m0-6-6 6"/></svg>',
    "critical": '<svg viewBox="0 0 24 24"><path d="M12 3 5 6v5c0 5 3 8 7 10 4-2 7-5 7-10V6l-7-3Z"/><path d="M12 8v5m0 4h.01"/></svg>',
}


def process_blockquotes(html_text):
    aliases = {
        "note": "note",
        "info": "info",
        "tip": "tip",
        "warning": "warning",
        "error": "error",
        "critical": "critical",
    }

    def classify(m):
        content = m.group(1)
        parts = re.findall(r"<p>(.*?)</p>", content, flags=re.DOTALL) or [content]
        expanded_parts = []
        for part in parts:
            expanded_parts.extend(
                re.split(
                    r"(?=<strong>\s*(?:Note|Info|Tip|Warning|Error|Critical)\s*</strong>)",
                    part,
                    flags=re.IGNORECASE,
                )
            )
        callouts = []
        for part in (part for part in expanded_parts if part.strip()):
            title = re.search(
                r"<strong>\s*(Note|Info|Tip|Warning|Error|Critical)\s*</strong>",
                part,
                re.IGNORECASE,
            )
            callout_type = (
                aliases.get(title.group(1).lower(), "info") if title else "info"
            )
            body = f"<p>{part}</p>"
            callouts.append(
                f'<div class="callout callout-{callout_type}">'
                f'<span class="callout-icon" aria-hidden="true">{CALLOUT_ICONS[callout_type]}</span>'
                f'<div class="callout-content">{body}</div></div>'
            )
        return "".join(callouts)

    return re.sub(
        r"<blockquote>\s*(.*?)\s*</blockquote>", classify, html_text, flags=re.DOTALL
    )


def format_ext_tags(html_text):
    return html_text.replace("[ext]", '<span class="ext-tag">ext</span>')
