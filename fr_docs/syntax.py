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

BASH_KEYWORDS = {
    "if",
    "then",
    "else",
    "elif",
    "fi",
    "for",
    "while",
    "until",
    "do",
    "done",
    "case",
    "esac",
    "in",
    "function",
    "return",
    "exit",
    "break",
    "continue",
    "local",
    "declare",
    "readonly",
    "export",
    "source",
    "alias",
    "unalias",
    "set",
    "unset",
    "shift",
    "trap",
    "wait",
    "exec",
    "eval",
    "let",
    "select",
    "time",
    "coproc",
    "mapfile",
    "readarray",
}

JSON_KEYWORDS = {"true", "false", "null"}

YAML_KEYWORDS = {"true", "false", "null", "yes", "no", "on", "off"}

TOKEN_SPECS = [
    (
        "st",
        r'""".*?"""|\'\'\'.*?\'\'\'',
    ),
    ("st", r'f?"(?:[^&]|&(?!quot;))*?"|f?\'(?:[^&]|&(?!#x27;))*?\''),
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

# Bash highlighting
BASH_TOKEN_SPECS = [
    ("cm", r"#[^\n]*"),
    ("st", r'"(?:[^&]|&(?!quot;))*?"|\'(?:[^&]|&(?!#x27;))*?\''),
    ("nb", r"\b\d+\.?\d*\b"),
    (
        "kw",
        r"\b(?:" + "|".join(sorted(BASH_KEYWORDS, key=len, reverse=True)) + r")\b",
    ),
]
BASH_HIGHLIGHT_CLASSES = [cls for cls, _ in BASH_TOKEN_SPECS]
BASH_HIGHLIGHT_PATTERN = "|".join(
    f"(?P<g{i}>{pat})" for i, (_, pat) in enumerate(BASH_TOKEN_SPECS)
)
BASH_HIGHLIGHT_RE = re.compile(BASH_HIGHLIGHT_PATTERN, flags=re.DOTALL)

# JSON highlighting
JSON_TOKEN_SPECS = [
    ("st", r'"(?:[^&]|&(?!quot;))*?"'),
    ("nb", r"\b\d+\.?\d*\b"),
    (
        "kw",
        r"\b(?:" + "|".join(sorted(JSON_KEYWORDS, key=len, reverse=True)) + r")\b",
    ),
]
JSON_HIGHLIGHT_CLASSES = [cls for cls, _ in JSON_TOKEN_SPECS]
JSON_HIGHLIGHT_PATTERN = "|".join(
    f"(?P<g{i}>{pat})" for i, (_, pat) in enumerate(JSON_TOKEN_SPECS)
)
JSON_HIGHLIGHT_RE = re.compile(JSON_HIGHLIGHT_PATTERN, flags=re.DOTALL)

# YAML highlighting
YAML_TOKEN_SPECS = [
    ("cm", r"#[^\n]*"),
    ("st", r'"(?:[^&]|&(?!quot;))*?"|\'(?:[^&]|&(?!#x27;))*?\''),
    ("nb", r"\b\d+\.?\d*\b"),
    (
        "kw",
        r"\b(?:" + "|".join(sorted(YAML_KEYWORDS, key=len, reverse=True)) + r")\b",
    ),
]
YAML_HIGHLIGHT_CLASSES = [cls for cls, _ in YAML_TOKEN_SPECS]
YAML_HIGHLIGHT_PATTERN = "|".join(
    f"(?P<g{i}>{pat})" for i, (_, pat) in enumerate(YAML_TOKEN_SPECS)
)
YAML_HIGHLIGHT_RE = re.compile(YAML_HIGHLIGHT_PATTERN, flags=re.DOTALL)


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


def highlight_bash(code):
    """Highlight Bash tokens using the precompiled regex."""

    def _replacer(m):
        for i, cls in enumerate(BASH_HIGHLIGHT_CLASSES):
            if m.group(f"g{i}") is not None:
                return f'<span class="{cls}">{m.group(f"g{i}")}</span>'
        return m.group(0)

    return BASH_HIGHLIGHT_RE.sub(_replacer, code)


def highlight_json(code):
    """Highlight JSON tokens using the precompiled regex."""

    def _replacer(m):
        for i, cls in enumerate(JSON_HIGHLIGHT_CLASSES):
            if m.group(f"g{i}") is not None:
                return f'<span class="{cls}">{m.group(f"g{i}")}</span>'
        return m.group(0)

    return JSON_HIGHLIGHT_RE.sub(_replacer, code)


def highlight_yaml(code):
    """Highlight YAML tokens using the precompiled regex."""

    def _replacer(m):
        for i, cls in enumerate(YAML_HIGHLIGHT_CLASSES):
            if m.group(f"g{i}") is not None:
                return f'<span class="{cls}">{m.group(f"g{i}")}</span>'
        return m.group(0)

    return YAML_HIGHLIGHT_RE.sub(_replacer, code)


def highlight_code_blocks(html_text):
    """Apply highlighting to <pre><code class=\"language-...\"> blocks."""

    def replace_block(m):
        lang = m.group(1) or ""
        inner = m.group(2)
        if "python" in lang or "py" in lang:
            inner = highlight_python(inner)
        elif "bash" in lang or "sh" in lang or "shell" in lang or "zsh" in lang:
            inner = highlight_bash(inner)
        elif "json" in lang:
            inner = highlight_json(inner)
        elif "yaml" in lang or "yml" in lang:
            inner = highlight_yaml(inner)
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