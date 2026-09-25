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

## Overview

Fr-docs is a generic, configurable documentation builder for Python projects. It converts Markdown source files into a searchable, optimized static HTML site with zero-config setup.

### Key Features

- **Config-driven**: All settings defined in `config.json`
- **Zero-config setup**: Works out of the box with sensible defaults
- **Search**: Full-text search with Zstandard-compressed index
- **Optimized**: HTML minification, critical CSS/JS inlining, Zstd compression
- **Multi-environment**: Different configs for production, staging, development
- **Parallel builds**: Threaded page generation for faster builds
- **Git integration**: Automatic metadata extraction from git commits

### Projects that use fr-docs

- [Fr-docs](https://omena0.dev/fr-docs/)
- [PyJavaBridge](https://omena0.dev/PyJavaBridge)
