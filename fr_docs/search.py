"""Search index building for fr-docs."""

import os
import re

from .config_accessors import feature_enabled
from .frontmatter import parse_frontmatter
from .slug import normalize_slug, slug_output_name, slug_page_key
from .utils import output_href


# Symbol extraction patterns for various languages
SYMBOL_PATTERNS = {
    'python': [
        (re.compile(r'^\s*def\s+(\w+)', re.MULTILINE), 'function'),
        (re.compile(r'^\s*class\s+(\w+)', re.MULTILINE), 'class'),
        (re.compile(r'^\s*async\s+def\s+(\w+)', re.MULTILINE), 'function'),
        (re.compile(r'^\s*@(\w+)\s*\n\s*def\s+(\w+)', re.MULTILINE), 'decorator_function'),
    ],
    'javascript': [
        (re.compile(r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)', re.MULTILINE), 'function'),
        (re.compile(r'^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>', re.MULTILINE), 'function'),
        (re.compile(r'^\s*class\s+(\w+)', re.MULTILINE), 'class'),
        (re.compile(r'^\s*(?:export\s+)?const\s+(\w+)\s*=', re.MULTILINE), 'variable'),
    ],
    'typescript': [
        (re.compile(r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)', re.MULTILINE), 'function'),
        (re.compile(r'^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>', re.MULTILINE), 'function'),
        (re.compile(r'^\s*class\s+(\w+)', re.MULTILINE), 'class'),
        (re.compile(r'^\s*interface\s+(\w+)', re.MULTILINE), 'interface'),
        (re.compile(r'^\s*type\s+(\w+)', re.MULTILINE), 'type'),
        (re.compile(r'^\s*enum\s+(\w+)', re.MULTILINE), 'enum'),
    ],
    'rust': [
        (re.compile(r'^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)', re.MULTILINE), 'function'),
        (re.compile(r'^\s*(?:pub\s+)?struct\s+(\w+)', re.MULTILINE), 'struct'),
        (re.compile(r'^\s*(?:pub\s+)?enum\s+(\w+)', re.MULTILINE), 'enum'),
        (re.compile(r'^\s*(?:pub\s+)?trait\s+(\w+)', re.MULTILINE), 'trait'),
        (re.compile(r'^\s*(?:pub\s+)?mod\s+(\w+)', re.MULTILINE), 'module'),
        (re.compile(r'^\s*(?:pub\s+)?const\s+(\w+)', re.MULTILINE), 'const'),
        (re.compile(r'^\s*(?:pub\s+)?static\s+(\w+)', re.MULTILINE), 'static'),
    ],
    'go': [
        (re.compile(r'^\s*func\s+(?:\([^)]*\)\s+)?(\w+)', re.MULTILINE), 'function'),
        (re.compile(r'^\s*type\s+(\w+)\s+struct', re.MULTILINE), 'struct'),
        (re.compile(r'^\s*type\s+(\w+)\s+interface', re.MULTILINE), 'interface'),
        (re.compile(r'^\s*const\s+(\w+)', re.MULTILINE), 'const'),
        (re.compile(r'^\s*var\s+(\w+)', re.MULTILINE), 'variable'),
    ],
    'java': [
        (re.compile(r'^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?\w+\s+(\w+)\s*\(', re.MULTILINE), 'method'),
        (re.compile(r'^\s*(?:public|private|protected)?\s*class\s+(\w+)', re.MULTILINE), 'class'),
        (re.compile(r'^\s*(?:public|private|protected)?\s*interface\s+(\w+)', re.MULTILINE), 'interface'),
        (re.compile(r'^\s*(?:public|private|protected)?\s*enum\s+(\w+)', re.MULTILINE), 'enum'),
    ],
    'c': [
        (re.compile(r'^\s*(?:static\s+)?\w+\s+(\w+)\s*\([^)]*\)\s*{', re.MULTILINE), 'function'),
        (re.compile(r'^\s*struct\s+(\w+)', re.MULTILINE), 'struct'),
        (re.compile(r'^\s*enum\s+(\w+)', re.MULTILINE), 'enum'),
    ],
    'cpp': [
        (re.compile(r'^\s*(?:static\s+)?\w+\s+(\w+)\s*\([^)]*\)\s*{', re.MULTILINE), 'function'),
        (re.compile(r'^\s*class\s+(\w+)', re.MULTILINE), 'class'),
        (re.compile(r'^\s*struct\s+(\w+)', re.MULTILINE), 'struct'),
        (re.compile(r'^\s*enum\s+(\w+)', re.MULTILINE), 'enum'),
        (re.compile(r'^\s*namespace\s+(\w+)', re.MULTILINE), 'namespace'),
    ],
    'csharp': [
        (re.compile(r'^\s*(?:public|private|protected|internal)?\s*(?:static\s+)?\w+\s+(\w+)\s*\(', re.MULTILINE), 'method'),
        (re.compile(r'^\s*(?:public|private|protected|internal)?\s*class\s+(\w+)', re.MULTILINE), 'class'),
        (re.compile(r'^\s*(?:public|private|protected|internal)?\s*interface\s+(\w+)', re.MULTILINE), 'interface'),
        (re.compile(r'^\s*(?:public|private|protected|internal)?\s*enum\s+(\w+)', re.MULTILINE), 'enum'),
        (re.compile(r'^\s*(?:public|private|protected|internal)?\s*struct\s+(\w+)', re.MULTILINE), 'struct'),
    ],
}


def get_language_from_path(file_path):
    """Determine language from file extension."""
    ext = file_path.split('.').pop().lower()
    lang_map = {
        'py': 'python',
        'js': 'javascript', 'jsx': 'javascript', 'mjs': 'javascript', 'cjs': 'javascript',
        'ts': 'typescript', 'tsx': 'typescript',
        'rs': 'rust',
        'go': 'go',
        'java': 'java',
        'c': 'c', 'h': 'c',
        'cpp': 'cpp', 'cc': 'cpp', 'cxx': 'cpp', 'hpp': 'cpp', 'hxx': 'cpp',
        'cs': 'csharp',
    }
    return lang_map.get(ext)


def extract_symbols_from_content(content, language):
    """Extract symbols (functions, classes, etc.) from source code content."""
    if not language or language not in SYMBOL_PATTERNS:
        return []
    
    symbols = []
    patterns = SYMBOL_PATTERNS[language]
    
    for pattern, symbol_type in patterns:
        for match in pattern.finditer(content):
            # Get the matched group - usually group 1 is the name
            if match.lastindex and match.lastindex >= 1:
                name = match.group(1)
            else:
                name = match.group(0)
            
            # Get line number
            line_num = content[:match.start()].count('\n') + 1
            
            # Get some context (the line itself)
            lines = content.split('\n')
            context = lines[line_num - 1].strip() if line_num <= len(lines) else ''
            
            symbols.append({
                'name': name,
                'type': symbol_type,
                'line': line_num,
                'context': context[:200],  # Limit context length
            })
    
    return symbols


def build_symbol_index(source_files, config):
    """Build a search index of symbols from source files."""
    symbol_index = []
    
    if not feature_enabled(config, "search"):
        return symbol_index
    
    for file_path, content in source_files.items():
        language = get_language_from_path(file_path)
        if not language:
            continue
        
        symbols = extract_symbols_from_content(content, language)
        
        for symbol in symbols:
            symbol_index.append({
                'file': file_path,
                'name': symbol['name'],
                'type': symbol['type'],
                'line': symbol['line'],
                'context': symbol['context'],
                'language': language,
            })
    
    return symbol_index


def _parse_search_sections(body_md):
    """Extract searchable text sections from markdown body."""
    title = None
    current_heading = title

    sections = []
    in_table = False

    table_first_cols = []
    table_header_seen = False

    for line in body_md.split("\n"):
        stripped = line.strip()

        if stripped.startswith("|") and "|" in stripped[1:]:
            if re.match(r"^\|[\s\-:|]+\|$", stripped):
                table_header_seen = True
                continue

            if not in_table:
                in_table = True
                table_header_seen = False
                continue

            if not table_header_seen:
                continue

            if cols := [c.strip() for c in stripped.strip("|").split("|")]:
                if col := re.sub(r"[`*\[\]()]", "", cols[0]).strip():
                    table_first_cols.append(col)

            continue

        else:
            if in_table and table_first_cols:
                sections.append(
                    {
                        "heading": current_heading,
                        "text": ", ".join(table_first_cols),
                    }
                )
                table_first_cols = []

            in_table = False
            table_header_seen = False

        if stripped.startswith("#"):
            current_heading = stripped.lstrip("#").strip()

        elif (stripped
                and not stripped.startswith("```")
                and not stripped.startswith("---")
            ):
            if clean := re.sub(r"[`*\[\]()]", "", stripped):
                sections.append({"heading": current_heading, "text": clean})

    if table_first_cols:
        sections.append(
            {"heading": current_heading, "text": ", ".join(table_first_cols)}
        )

    return sections


def _extract_links(body_md):
    """Extract all markdown links from body."""
    links = []
    # Match [text](url) but not images ![text](url)
    link_pattern = re.compile(r'(?<!\!)\[([^\]]+)\]\(([^)]+)\)')
    for match in link_pattern.finditer(body_md):
        target = match.group(2).strip()
        # Only consider internal .md links
        if target.endswith('.md') or (not target.startswith('http') and not target.startswith('mailto:') and not target.startswith('#') and ':' not in target):
            # Remove .md extension
            target = target.replace('.md', '').replace('.html', '')
            links.append(target)
    return links


def _resolve_link(link, current_slug, slug_to_source, slug_to_idx, config, search_index):
    """Resolve a link to a target slug."""
    # Try direct match
    if link in slug_to_source:
        return search_index[slug_to_source[link]]['slug']
    # Try normalized
    norm = normalize_slug(link)
    if norm in slug_to_source:
        return search_index[slug_to_source[norm]]['slug']
    # Try relative to current page
    if current_slug:
        base_dir = current_slug.rsplit('/', 1)[0] if '/' in current_slug else ''
        if base_dir:
            rel_link = normalize_slug(f"{base_dir}/{link}")
            if rel_link in slug_to_source:
                return search_index[slug_to_source[rel_link]]['slug']
    return None


def _compute_backlinks_and_related(search_index, config):
    """Compute backlinks and related pages for each page."""
    # Build a map of page slugs to their index
    slug_to_idx = {item['slug']: i for i, item in enumerate(search_index)}
    slug_to_source = {item['source_slug']: i for i, item in enumerate(search_index)}
    
    # First pass: collect all links from each page
    page_links = {}  # slug -> set of target slugs
    for i, item in enumerate(search_index):
        src = os.path.join(config["_src_dir"], f"{item['source_slug']}.md")
        if os.path.exists(src):
            with open(src, "r", encoding="utf-8") as f:
                raw = f.read()
            _, body_md = parse_frontmatter(raw)
            links = _extract_links(body_md)
            # Resolve links to actual slugs
            resolved = set()
            for link in links:
                resolved_slug = _resolve_link(link, item['source_slug'], slug_to_source, slug_to_idx, config, search_index)
                if resolved_slug:
                    resolved.add(resolved_slug)
            page_links[item['slug']] = resolved
    
    # Compute backlinks (reverse links)
    backlinks = {item['slug']: set() for item in search_index}
    for source_slug, targets in page_links.items():
        for target_slug in targets:
            backlinks[target_slug].add(source_slug)
    
    # Compute related pages (simple: pages that share links or are linked together)
    related = {item['slug']: set() for item in search_index}
    for i, item in enumerate(search_index):
        # Pages that link to the same targets
        source_links = page_links.get(item['slug'], set())
        for other_item in search_index:
            if other_item['slug'] == item['slug']:
                continue
            other_links = page_links.get(other_item['slug'], set())
            # If they share at least one link target, they're related
            if source_links & other_links:
                related[item['slug']].add(other_item['slug'])
            # If they link to each other, they're related
            if item['slug'] in other_links or other_item['slug'] in source_links:
                related[item['slug']].add(other_item['slug'])
    
    # Convert to sorted lists and add to search index
    for item in search_index:
        slug = item['slug']
        bl = sorted(backlinks.get(slug, []))
        rel = sorted(related.get(slug, []))
        # Limit to reasonable numbers
        item['backlinks'] = bl[:50]
        item['related'] = rel[:12]


def build_search_index(slugs, config):
    """Build the search index from markdown sources."""
    search_index = []

    for slug in slugs:
        src = os.path.join(config["_src_dir"], f"{slug}.md")

        if os.path.exists(src):
            with open(src, "r", encoding="utf-8") as f:
                raw = f.read()

            meta, body_md = parse_frontmatter(raw)

            title = meta.get("title", slug.capitalize())
            sections = _parse_search_sections(body_md)

            page_key = slug_page_key(slug, config)
            url = output_href(slug_output_name(slug, config), config)
            search_index.append(
                {
                    "slug": page_key,
                    "source_slug": normalize_slug(slug),
                    "title": title,
                    "url": url,
                    "sections": sections,
                }
            )

    config["search_map"] = {}
    for item in search_index:
        title = item.get("title") or ""
        source_slug = item.get("source_slug") or item.get("slug")
        if not title or not source_slug:
            continue

        cleaned = re.sub(r"\[ext\]", "", title)
        cleaned = re.sub(r"[`*()]+", "", cleaned).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)

        config["search_map"][cleaned] = f"{source_slug}.md"
        if title != cleaned:
            config["search_map"][title] = f"{source_slug}.md"

    # Build symbol index from source files if code_references is enabled
    if feature_enabled(config, "code_references") and config.get("_source_files"):
        symbol_index = build_symbol_index(config["_source_files"], config)
        config["_symbol_index"] = symbol_index
        
        # Add symbols to search_map for auto-linking
        for symbol in symbol_index:
            config["search_map"][symbol['name']] = f"#{symbol['file']}:{symbol['line']}"

    # Compute backlinks and related if enabled
    if feature_enabled(config, "backlinks") or feature_enabled(config, "related"):
        _compute_backlinks_and_related(search_index, config)
    else:
        # Ensure fields exist but empty
        for item in search_index:
            item['backlinks'] = []
            item['related'] = []

    return search_index
