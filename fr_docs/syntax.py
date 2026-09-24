"""Syntax highlighting and HTML preprocessing for fr-docs."""

import re

PYTHON_KEYWORDS = {
    "False",
    "None",
    "True",
    "and",
    "as",
    "assert",
    "async",
    "await",
    "break",
    "class",
    "continue",
    "def",
    "del",
    "elif",
    "else",
    "except",
    "finally",
    "for",
    "from",
    "global",
    "if",
    "import",
    "in",
    "is",
    "lambda",
    "nonlocal",
    "not",
    "or",
    "pass",
    "raise",
    "return",
    "try",
    "while",
    "with",
    "yield",
}

TOKEN_SPECS = [
    (
        "st",
        r"&quot;&quot;&quot;.*?&quot;&quot;&quot;|&#x27;&#x27;&#x27;.*?&#x27;&#x27;&#x27;",
    ),
    ("st", r"f?&quot;(?:[^&]|&(?!quot;))*?&quot;|f?&#x27;(?:[^&]|&(?!#x27;))*?&#x27;"),
    ("cm", r"#[^\n]*"),
    ("dc", r"@\w+"),
    ("nb", r"\b\d+\.?\d*\b"),
    (
        "kw",
        r"\b(?:" + "|".join(sorted(PYTHON_KEYWORDS, key=len, reverse=True)) + r")\b",
    ),
]

HIGHLIGHT_CLASSES = [cls for cls, _ in TOKEN_SPECS]
HIGHLIGHT_PATTERN = "|".join(
    f"(?P<g{i}>{pat})" for i, (_, pat) in enumerate(TOKEN_SPECS)
)
HIGHLIGHT_RE = re.compile(HIGHLIGHT_PATTERN, flags=re.DOTALL)

PRE_CODE_RE = re.compile(
    r'<pre><code class="language-(\w*)">(.*?)</code></pre>', flags=re.DOTALL
)
URL_ATTR_RE = re.compile(
    r'(?P<attr>\b(?:href|src))\s*=\s*(?P<quote>["\']?)(?P<url>[^"\'\s>]+)(?P=quote)',
    flags=re.IGNORECASE,
)


def highlight_python(code):
    """Highlight Python-like tokens using the precompiled regex."""

    def _replacer(m):
        for i, cls in enumerate(HIGHLIGHT_CLASSES):
            if m.group(f"g{i}") is not None:
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


def process_blockquotes(html_text):
    def classify(m):
        content = m.group(1)
        if content.strip().startswith("<strong>Warning"):
            cls = "callout callout-warn"
        elif content.strip().startswith("<strong>Tip"):
            cls = "callout callout-tip"
        elif content.strip().startswith("<strong>Note") or content.strip().startswith(
            "<strong>See also"
        ):
            cls = "callout callout-info"
        else:
            cls = "callout callout-info"

        return f'<div class="{cls}">{content}</div>'

    return re.sub(
        r"<blockquote>\s*(.*?)\s*</blockquote>", classify, html_text, flags=re.DOTALL
    )


def format_ext_tags(html_text):
    return html_text.replace("[ext]", '<span class="ext-tag">ext</span>')