# Search

Fr-docs includes a full-text search engine powered by Zstandard compression.

## How It Works

1. Build generates a search index
2. Index is compressed with Zstandard (`.zst` extension)
3. Search queries are performed client-side
4. Results are displayed inline

## Configuration

```json
{
  "build": {
    "search_index_filename": "search_index.zst",
    "zstd_level": 22
  }
}
```

## Search Levels

The search engine supports different levels:

- **Level 1**: Basic search (title only)
- **Level 2**: Standard search (title + content)
- **Level 3**: Fuzzy search (title + content + fuzzy matching)
- **Level 4**: Advanced search (title + content + fuzzy + relevance scoring)
- **Level 5**: Expert search (all features + custom scoring)

```bash
fr-docs build --search --search-level 5
```

## Search Index Format

The search index is a Zstandard-compressed JSON file containing:

- Page titles
- Page content (stripped of HTML)
- Page URLs
- Metadata (author, date, etc.)

## Client-Side Search

The search functionality is implemented in JavaScript and runs entirely in the browser. No server-side processing is required.

## Performance

- Zstd compression reduces index size by 70-90%
- Client-side search provides instant results
- Index is cached for subsequent builds