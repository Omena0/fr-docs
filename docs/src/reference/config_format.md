# Config Format

## Complete Configuration

```json
{
  "project_name": "My Project",
  "project_url": "https://github.com/your-org/my-project",
  "site_path_prefix": "/my-project/",
  "docs_dir": "docs",
  "src_dir": "src",
  "out_dir": "site",
  "sidebar": [
    ["Category Name", [
      ["page_slug", "Display Title"],
      ["another_page", "Another Title"]
    ]]
  ],
  "build": {
    "workers": 4,
    "minify_html": true,
    "optimize_html": true,
    "zstd_level": 22,
    "search_index_filename": "search_index.zst",
    "git_meta_filename": "git_meta.json",
    "include_git_metadata": true
  },
  "versioning": {
    "commit_message_pattern": "^\\s*([0-9]+[A-Za-z])\\s*[-:—–]\\s*(.+)",
    "live_label": "Live"
  }
}
```

## Field Reference

### project_name (string, required)
The display name for the project.

### project_url (string, optional)
Link to the project repository. Used in the header.

### site_path_prefix (string, default: "/")
The base URL path for deployment. For example, `/my-project/` for `https://your-repo.pages.dev/my-project/`.

### docs_dir (string, default: ".")
The root directory for documentation files.

### src_dir (string, default: "src")
The source markdown directory (relative to docs_dir).

### out_dir (string, default: "site")
The output directory (relative to docs_dir).

### sidebar (array, required)
The navigation sidebar structure. Each element is either:
- A category: `[category_title, [page_slug, display_title]]`
- A page: `[page_slug, display_title]`

### build.workers (integer, default: 4)
Number of parallel workers for building pages.

### build.minify_html (boolean, default: true)
Whether to minify HTML output.

### build.optimize_html (boolean, default: true)
Whether to optimize HTML (inline critical CSS/JS).

### build.zstd_level (integer, default: 22)
Zstandard compression level for search index.

### build.search_index_filename (string, default: "search_index.zst")
Filename for the search index.

### build.git_meta_filename (string, default: "git_meta.json")
Filename for git metadata.

### build.include_git_metadata (boolean, default: true)
Whether to include git metadata in the build.

### versioning.commit_message_pattern (string, default: "^\s*([0-9]+[A-Za-z])\s*[-:—–]\s*(.+)")
Regex pattern for extracting version from commit messages.

### versioning.live_label (string, default: "Live")
Label for the latest version in versioned URLs.