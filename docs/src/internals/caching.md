# Caching

## Overview

Fr-docs supports caching to speed up repeated builds.

## Cache Files

- `search_index.zst` - Compressed search index
- `git_meta.json` - Git metadata
- HTML output files in `docs/site/`

## Build Cache

The build cache stores:
- Generated HTML pages
- Search index
- Git metadata
- Build statistics

## Cache Options

### Enable Cache

```bash
fr-docs build --use-cache
```

### Clear Cache

```bash
fr-docs build --clear-cache
```

### Resume Build

```bash
fr-docs build --resume
```

## Cache Invalidation

The cache is invalidated when:
- Markdown source files change
- Configuration changes
- Template changes
- Build options change

## Performance

Caching can significantly reduce build time for large documentation sites by skipping unchanged pages.

## Search Index

The search index is rebuilt when:
- Source content changes
- Search options change
- Compression settings change

## Git Metadata

Git metadata is refreshed when:
- Git repository state changes
- Metadata settings change

## Best Practices

1. Use `--use-cache` for frequent builds
2. Use `--clear-cache` when troubleshooting
3. Use `--resume` for interrupted builds
4. Keep `docs/src/` and `docs/site/` separate