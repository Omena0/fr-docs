# Architecture

## Overview

Fr-docs is a static documentation builder with a modular architecture:

```text
fr_docs/
├── __init__.py      # Package version and exports
├── __main__.py      # `python -m fr_docs` entry point
├── build.py         # Build logic
├── config.py        # Configuration loading
└── template.py      # HTML template
```

## Build Pipeline

1. **Load Configuration**
   - Read `config.json`
   - Merge with defaults
   - Resolve paths

2. **Discover Pages**
   - Find markdown files in `docs/src/`
   - Build page registry

3. **Generate HTML**
   - Convert Markdown to HTML
   - Apply template
   - Minify output

4. **Build Search Index**
   - Extract text content
   - Compress with Zstandard
   - Write `search_index.zst`

5. **Optimize**
   - Inline critical CSS/JS
   - Generate versioned URLs

## Modules

### build.py
The main build engine. Handles page generation, search indexing, and optimization.

### config.py
Loads and validates configuration from `config.json`.

### template.py
Provides the HTML template for generated pages.

### __main__.py
Enables `python -m fr_docs` usage.

## Dependency Management

Fr-docs uses standard Python libraries plus:
- `markdown` for Markdown parsing
- `zstandard` for search index compression
- `html-minifier-next` for HTML minification
- `critical` for CSS/JS optimization

## Threading

The builder supports parallel page generation using configurable worker count:

```json
{
  "build": {
    "workers": 4
  }
}
```