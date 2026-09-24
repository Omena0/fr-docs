# Configuration

Fr-docs is configured via a `config.json` file in your project root.

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `project_name` | string | Display name for the project |
| `sidebar` | array | Navigation sidebar structure |

## Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `project_url` | string | `""` | Link to project repository |
| `docs_dir` | string | `"."` | Root directory for docs |
| `src_dir` | string | `"src"` | Source markdown directory (relative to docs_dir) |
| `out_dir` | string | `"site"` | Output directory (relative to docs_dir) |
| `site_path_prefix` | string | `"/"` | Base URL path for deployment |

## Build Settings

```json
{
  "build": {
    "workers": 4,
    "minify_html": true,
    "optimize_html": true,
    "zstd_level": 22,
    "search_index_filename": "search_index.zst",
    "git_meta_filename": "git_meta.json"
  }
}
```

## Versioning

```json
{
  "versioning": {
    "commit_message_pattern": "^\\s*([0-9]+[A-Za-z])\\s*[-:—–]\\s*(.+)",
    "live_label": "Live"
  }
}
```

## Sidebar Format

The sidebar is an array of categories, each containing a title and array of pages:

```json
[
  ["Category Name", [
    ["page_slug", "Display Title"],
    ["another_page", "Another Title"]
  ]],
  ["Another Category", [
    ["page_slug", "Display Title"]
  ]]
]
```

The `page_slug` corresponds to `docs/src/page_slug.md`.