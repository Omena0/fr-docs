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
# HTML content has already been escaped, so we match both raw quotes and HTML entities
# Strings are matched FIRST so comments inside strings are not highlighted
# Opening/closing quotes: " or " or " or "
# Content: any character except unescaped quote or backslash
JSON_TOKEN_SPECS = [
    ("punct-brace", r"[\[\]]"),       # square brackets - color 1
    ("punct-brace", r"[\{\}]"),       # curly braces - color 1 (same as brackets)
    ("punct-comma", r","),            # commas
    ("punct-colon", r":"),            # colons
    ("st", r'''(?:"|"|"|")(?:\\.|[^"\\])*(?:"|"|"|")'''),  # double-quoted strings
    ("st", r"""(?:'|&apos;)(?:\\.|[^'\\])*(?:'|&apos;)"""),  # single-quoted strings
    ("cm", r"//[^\n]*|/\*[\s\S]*?\*/"),  # comments (JS-style)
    ("kw", r"\b(?:true|false|null)\b"),
    ("nb", r"-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b"),  # numbers including scientific
]
JSON_HIGHLIGHT_CLASSES = [cls for cls, _ in JSON_TOKEN_SPECS]
JSON_HIGHLIGHT_PATTERN = "|".join(
    f"(?P<g{i}>{pat})" for i, (_, pat) in enumerate(JSON_TOKEN_SPECS)
)
JSON_HIGHLIGHT_RE = re.compile(JSON_HIGHLIGHT_PATTERN, flags=re.DOTALL)

# YAML highlighting
YAML_TOKEN_SPECS = [
    ("punct-brace", r"[\[\]]"),      # square brackets
    ("punct-brace", r"[\{\}]"),       # curly braces
    ("punct-comma", r","),            # commas
    ("punct-colon", r":"),            # colons
    ("st", r'''(?:"|"|"|")(?:\\.|[^"\\])*(?:"|"|"|")'''),  # double-quoted strings
    ("st", r"""(?:'|&apos;)(?:\\.|[^'\\])*(?:'|&apos;)"""),  # single-quoted strings
    ("cm", r"#[^\n]*"),  # comments
    ("kw", r"\b(?:true|false|null|yes|no|on|off)\b"),
    ("nb", r"-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b"),  # numbers
    ("key", r"^\s*[a-zA-Z_][a-zA-Z0-9_-]*\s*:"),  # keys at start of line
]
YAML_HIGHLIGHT_CLASSES = [cls for cls, _ in YAML_TOKEN_SPECS]
YAML_HIGHLIGHT_PATTERN = "|".join(
    f"(?P<g{i}>{pat})" for i, (_, pat) in enumerate(YAML_TOKEN_SPECS)
)
YAML_HIGHLIGHT_RE = re.compile(YAML_HIGHLIGHT_PATTERN, flags=re.MULTILINE | re.DOTALL)


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


def _extract_strings(code, quote_chars=None):
    """Extract quoted strings from code, replacing them with placeholders.

    Returns (modified_code, strings_list) where strings_list contains
    the extracted strings in order.
    Handles both literal quotes and HTML entities (quot;, apos;).
    """
    if quote_chars is None:
        quote_chars = ('"', "'", "&quot;", "&apos;")

    strings = []
    placeholder_base = "@@STRING_PLACEHOLDER_"

    # Pattern to match quoted strings (handles escaped quotes and HTML entities)
    quote_pattern = '|'.join(re.escape(q) for q in quote_chars)

    # Simpler approach: match each quote type separately with proper HTML entity support
    patterns = []
    for q in quote_chars:
        eq = re.escape(q)
        patterns.append(f'{eq}(?:\\\\.|(?:(?!{eq})[^\\\\]))*{eq}')

    combined_pattern = '|'.join(patterns)
    string_re = re.compile(combined_pattern)

    def replace_string(m):
        strings.append(m.group(0))
        return f"{placeholder_base}{len(strings) - 1}@@"

    modified = string_re.sub(replace_string, code)

    return modified, strings


def _restore_strings(code, strings):
    """Restore strings from placeholders."""
    for i, s in enumerate(strings):
        code = code.replace(f"@@STRING_PLACEHOLDER_{i}@@", s)
    return code


def highlight_json(code):
    """Highlight JSON tokens using the precompiled regex.

    First extracts strings to prevent punctuation inside strings from being highlighted.
    """
    import sys
    has_double_quote = '"' in code
    has_html_quote = '"' in code
    # Extract strings first
    code_no_strings, strings = _extract_strings(code)

    def _replacer(m):
        for i, cls in enumerate(JSON_HIGHLIGHT_CLASSES):
            if m.group(f"g{i}") is not None:
                return f'<span class="{cls}">{m.group(f"g{i}")}</span>'
        return m.group(0)

    highlighted = JSON_HIGHLIGHT_RE.sub(_replacer, code_no_strings)

    # Restore strings with their own highlighting
    for i, s in enumerate(strings):
        # Highlight the string itself (quotes as punctuation, content as string)
        highlighted_string = s
        # Replace opening quote
        highlighted_string = re.sub(r'^("|"|"|")', r'<span class="punct-quote">\1</span>', highlighted_string)
        # Replace closing quote
        highlighted_string = re.sub(r'("|"|"|")$', r'<span class="punct-quote">\1</span>', highlighted_string)
        # The content between quotes stays as-is (already escaped HTML)
        highlighted = highlighted.replace(f"@@STRING_PLACEHOLDER_{i}@@", f'<span class="st">{highlighted_string}</span>')

    return highlighted


def highlight_yaml(code):
    """Highlight YAML tokens using the precompiled regex.

    First extracts strings to prevent punctuation inside strings from being highlighted.
    """
    # Extract strings first
    code_no_strings, strings = _extract_strings(code)

    def _replacer(m):
        for i, cls in enumerate(YAML_HIGHLIGHT_CLASSES):
            if m.group(f"g{i}") is not None:
                return f'<span class="{cls}">{m.group(f"g{i}")}</span>'
        return m.group(0)

    highlighted = YAML_HIGHLIGHT_RE.sub(_replacer, code_no_strings)

    # Restore strings with their own highlighting
    for i, s in enumerate(strings):
        highlighted_string = s
        highlighted_string = re.sub(r'^("|"|"|")', r'<span class="punct-quote">\1</span>', highlighted_string)
        highlighted_string = re.sub(r'("|"|"|")$', r'<span class="punct-quote">\1</span>', highlighted_string)
        highlighted = highlighted.replace(f"@@STRING_PLACEHOLDER_{i}@@", f'<span class="st">{highlighted_string}</span>')

    return highlighted


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