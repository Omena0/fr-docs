# Fr-docs

Fr-docs is a generic, configurable documentation builder for Python projects. It converts Markdown source files into a searchable, optimized static HTML site with zero-config setup.

## Quick Links

- [Installation](installation.md)
- [Quickstart](quickstart.md)
- [Configuration](configuration.md)
- [Build Guide](../usage/build.md)
- [Search Features](../usage/search.md)
- [Versioning](../usage/versioning.md)
- [Deployment](../usage/deploy.md)
- [API Reference](../reference/api.md)
- [Config Format](../reference/config_format.md)
- [Version Format](../reference/version_format.md)
- [Markdown Format](../reference/markdown_format.md)
- [Architecture](../internals/architecture.md)
- [Caching](../internals/caching.md)

## Getting Started in 5 Minutes

1. Install fr-docs: `pip install fr-docs`
2. Create config.json with project settings
3. Add markdown files to `docs/src/`
4. Build: `fr-docs build`
5. Deploy: Upload `docs/site/` to your hosting provider

## Features

- **Config-driven**: All settings defined in `config.json`
- **Zero-config setup**: Works out of the box with sensible defaults
- **Search**: Full-text search with Zstandard-compressed index
- **Versioning**: Semantic versioning from commit messages (`4D - fix bug` → `4.4.0`)
- **Optimized**: HTML minification, critical CSS/JS inlining, Zstd compression
- **Multi-environment**: Different configs for production, staging, development
- **Parallel builds**: Threaded page generation for faster builds
- **Git integration**: Automatic metadata extraction from git commits

## Navigation

### Getting Started

- [Installation](installation.md) - Install fr-docs
- [Quickstart](quickstart.md) - Step-by-step tutorial
- [Configuration](configuration.md) - Configure your project

### Usage

- [Build Guide](../usage/build.md) - Build documentation
- [Search Features](../usage/search.md) - Full-text search
- [Versioning](../usage/versioning.md) - Automatic versioning
- [Deployment](../usage/deploy.md) - Deploy to hosting

### Reference

- [API Reference](../reference/api.md) - Command-line and Python API
- [Config Format](../reference/config_format.md) - Configuration file format
- [Version Format](../reference/version_format.md) - Version numbering
- [Markdown Format](../reference/markdown_format.md) - Markdown syntax guide

### Internals

- [Architecture](../internals/architecture.md) - System architecture
- [Caching](../internals/caching.md) - Build caching system
