
# Fr-docs

Generate fast, fully featured, modern documentation pages from markdown for GitHub pages and static hosting.

[![Lint](https://github.com/Omena0/fr-docs/actions/workflows/lint.yml/badge.svg)](https://github.com/Omena0/fr-docs/actions/workflows/lint.yml)
[![Docs](https://github.com/Omena0/fr-docs/actions/workflows/pages.yml/badge.svg)](https://github.com/Omena0/fr-docs/actions/workflows/pages.yml)
[![PyPi](https://github.com/Omena0/fr-docs/actions/workflows/publish.yml/badge.svg)](https://github.com/Omena0/fr-docs/actions/workflows/publish.yml)
[![CodeQL](https://github.com/Omena0/fr-docs/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/Omena0/fr-docs/actions/workflows/github-code-scanning/codeql)

## Documentation

- [Getting Started](https://omena0.dev/fr-docs/)
- [Installation](https://omena0.dev/fr-docs/installation)
- [Quickstart](https://omena0.dev/fr-docs/quickstart)
- [Configuration](https://omena0.dev/fr-docs/config.json)
- [Showcase](https://omena0.dev/fr-docs/showcase)
- [Pagespeed](https://omena0.dev/fr-docs/pagespeed) — performance metrics

## Overview

Fr-docs is a generic, configurable documentation builder for Python projects. It converts Markdown source files into a searchable, optimized static HTML site with zero-config setup.

### Key Features

- **Config-driven**: All settings defined in `config.json`
  - Project name, URL, description, and sidebar structure
  - Search, code references, auto-linking, and related pages
  - Build options: workers, minification, zstd level, and HTML optimization
- **Zero-config setup**: Works out of the box with sensible defaults
- **Search**: Full-text search with Zstandard-compressed index
  - Symbol-level search across all source files
  - File index for browsing source code
  - Per-file source highlights with caching
- **Optimized**: HTML minification, critical CSS/JS inlining, Zstd compression
  - Critical CSS extracted and inlined for both mobile and desktop viewports
  - JavaScript and CSS minified with `terser` and `html-minifier-next`
  - Zstd-compressed search index, source files, highlights, and metadata
  - Adaptive zstd level selection (scans 1..configured, picks the smallest)
- **Multi-environment**: Different configs for production, staging, development
- **Parallel builds**: Threaded page generation for faster builds
- **Git integration**: Automatic metadata extraction from git commits
  - Version options derived from commit messages (e.g. `4D - fix bug` → `4.4.0`)
  - Commit SHA and message embedded in the version selector
- **Local font serving**: Fonts downloaded at build time and served from the site's own origin
  - No third-party font round-trips or 404s when Google changes the URL scheme
  - `font-display: swap` with metric-compatible `font-ascent-descent` fallbacks
  - Primary body font weight preloaded for faster first paint
- **Sidebar**: Collapsible sections with auto-expansion
  - The section containing the current page is expanded on load
  - Single-page sections and single-section sites are expanded by default
- **Inline copy commands**: Prefix inline code with `c` to create copy-on-click links
- **Code references**: Auto-link bare filename references to their source files
- **Backlinks and related pages**: Automatically generated navigation between related content

### Projects that use fr-docs

- [Fr-docs](https://omena0.dev/fr-docs/)
- [PyJavaBridge](https://omena0.dev/PyJavaBridge)
