# Features Showcase

This page demonstrates all the features of fr-docs.

## 1. Code References

Code references can open a whole file, a specific line or range, or a function. File and function references are scrollable, and function references include attached decorators plus one line of context.

### File reference (entire file)

[fr_docs/syntax.py](fr_docs/syntax.py)

### Function reference

[highlight_code_blocks](fr_docs/syntax.py:highlight_code_blocks)

### Line range reference

[normalize_language](fr_docs/syntax.py:39-47)

Ranges highlight the first and last selected lines fully; intervening lines only show the range marker beside the line number.

### Inline and code-block references

[process_code_references_html()](fr_docs/markdown.py:process_code_references_html)

```python
# This references a function: [process_code_references_html](fr_docs/markdown.py:process_code_references_html)
def hello():
    pass
```

## 2. Filename Auto-linking

Bare filenames in **inline code** (backticks) are automatically linked to their documentation pages:

- `config.json` - Configuration reference
- `quickstart.md` - Quickstart guide  
- `installation.md` - Installation guide
- `index.md` - Home page

These do NOT link inside code blocks:

```json
{
  "files": ["config.json", "quickstart.md", "installation.md"]
}
```

## 3. Syntax Highlighting

Syntax highlighting is powered by [fastpylight](https://github.com/AnswerDotAI/fastpylight) and Lumis tree-sitter grammars. Python, JavaScript, JSON, Bash, and other supported languages are highlighted at build time with a GitHub Dark theme.

### Python

```python
def fibonacci(n: int) -> int:
    """Calculate nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


# Decorator example
@cache
def cached_fib(n):
    return fibonacci(n)


# Async example
async def fetch_data():
    await asyncio.sleep(0.1)
    return "data"
```

### JavaScript/TypeScript

```javascript
// Modern JS with async/await
async function fetchUser(id) {
  const response = await fetch(`/api/users/${id}`);
  if (!response.ok) throw new Error('User not found');
  return response.json();
}

// Arrow functions and destructuring
const processUser = ({ name, email }) => ({
  displayName: name.toUpperCase(),
  contact: email
});
```

### JSON (with URLs in strings - comments NOT highlighted inside strings)

```json
{
  "api": {
    "baseUrl": "https://api.example.com/v1",
    "endpoints": {
      "users": "/users",
      "posts": "/posts"
    }
  },
  "features": {
    "authentication": true,
    "rateLimiting": false
  },
  "version": "1.0.0"
}
```

### YAML (with comment-like content in strings)

```yaml
# Configuration file
server:
  host: "0.0.0.0"
  port: 8080
  # This is a real comment
  url: "https://example.com/path?query=value#fragment"

database:
  url: "postgresql://user:pass@localhost/db"
  pool_size: 10
  # Another comment
  options:
    ssl: true
    timeout: 30
```

### Bash/Shell

```bash
#!/bin/bash
# Build script for fr-docs

set -euo pipefail

# Function to build docs
build_docs() {
    local config="${1:-config.json}"
    echo "Building with config: $config"
    
    if [[ ! -f "$config" ]]; then
        echo "Config not found: $config" >&2
        return 1
    fi
    
    fr-docs build --config "$config"
}

# Main
for cfg in config*.json; do
    build_docs "$cfg" || exit 1
done

echo "All builds completed successfully!"
```

## 4. Inline Copy Commands

Prefix any inline code block with `c` to create a clickable copy link:

- c`pip install fr-docs`
- c`fr-docs build --config config.json`
- c`docker run -v $(pwd):/app myimage`

Hover over the commands above to see the "click to copy" tooltip, then click to copy.

## 5. Code Block Copy Buttons

Hover over any code block above to see the copy button in the top-right corner.

## 6. Search with Symbol and File Results

Search can include pages, page titles, headings, content, symbols, and source filenames. Configure these under `features.search.include`:

```json
"search": {
  "enabled": true,
  "include": {
    "pages": true,
    "titles": true,
    "headings": true,
    "content": true,
    "symbols": true,
    "files": true
  }
}
```

Try searching for:

- `process_code_references_html` (function)
- `highlight_code_blocks` (function)
- `config.json` (page or file)
- `syntax.py` (file)

Symbol and file results open a scrollable full-file code panel at the matching location.

## 6. Link Hover Previews

Hover over these links to see previews:

- [Configuration](config.json.md) - Page preview
- [Quickstart](quickstart.md) - Page preview

Hover over code references in code blocks to see code previews:

```python
# Hover over this: [highlight_code_blocks](fr_docs/syntax.py:highlight_code_blocks)
```

## 7. Callout Boxes (Blockquotes)

> **Note** This is a note callout box.
> **Info** This is an info callout box.
> **Tip** This is a tip callout box.
> **Warning** This is a warning callout box.
> **Error** This is an error callout box.
> **Critical** This is a critical callout box.

## 8. Extension Tags

This is an [ext] feature.

## 9. Tables

| Feature | Status | Description |
| --------- | -------- | ------------- |
| Code References | ✅ | File, line, range, and function links |
| Filename Links | ✅ | Auto-link inline filenames |
| Syntax Highlighting | ✅ | Python, JS, JSON, YAML, Bash |
| Search | ✅ | Configurable pages, symbols, and files |
| Version | 6.7.7 |
| Link Previews | ✅ | Hover previews |
| Inline Copy Commands | ✅ | c`command` to copy on click |

## 10. Lists

### Unordered

- Item 1
- Item 2 with `inline code`
- Item 3
  - Nested item
  - Another nested item

### Ordered

1. First step
2. Second step
3. Third step

## 11. Per-Page Feature Control

Use `<!no_backlinks>` or `<!no_related>` in your markdown to disable those features for a specific page:

```
<!no_backlinks>
<!no_related>
```

This page has both enabled (no disable tags).

## 12. Versioning

If viewing a historical version, you'll see a version badge in the header. The version selector in the top-right allows switching between versions.

## 13. Anchor Links

Hover over any heading to see the anchor link (¶) for direct linking.

## 14. Responsive Design

Resize your browser window to see the responsive sidebar and layout.

## 15. Dark Mode

fr-docs uses a dark theme by default with carefully chosen colors for readability.
