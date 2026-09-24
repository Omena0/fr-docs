"""Frontmatter parsing and HTML preprocessing for fr-docs."""


def parse_frontmatter(text):
    """Extract YAML-like frontmatter and return (metadata_dict, remaining_text)."""
    if not text.startswith("---"):
        return {}, text

    end = text.find("---", 3)
    if end == -1:
        return {}, text

    fm_block = text[3:end].strip()
    body = text[end + 3 :].strip()
    meta = {}
    for line in fm_block.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip()] = val.strip()

    return meta, body


def format_ext_tags(html_text):
    return html_text.replace("[ext]", '<span class="ext-tag">ext</span>')
