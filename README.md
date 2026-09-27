
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

- **Toggleable features**: Disable any features in the config.
- **Search**: Search pages, headers, source code files, or symbols. Fuzzy matching included.
- **Markdown features**: Feature-complete markdown features, including:
  - **Code highlighting**: Highlight code blocks with `fastpylight`
  - **Copy code blocks**: Copy buttons on multiline code blocks, inline copy code blocks.
  - **Tables**: Auto convert markdown tables
  - **Frontmatter metadata**: Title and description as optional frontmatter.
  - **Hover previews**: Hover a link to see the title and description, hover a code ref to see a code preview.
  - **Code references**: Link to a source code files, lines, line ranges, or symbols. Automatically generates a clickable code ref.
- **Auto versioned**: Automatically switch to older documentation based on github tags.

<sup><sub>(requires site/ to be commited into the repo)</sup></sub>
- **Auto minification**: Minifies HTML, CSS and JS and inlines Critical CSS.
- **Same-origin fonts**: Serve fonts from the same origin. Download once before build, serve forever.
- **Page preloading**: Preload page links for faster browsing.
- **Configurable elements**: Configure project name, icon, copyright, topbar links, etc.


### Projects that use fr-docs

- [Fr-docs](https://omena0.dev/fr-docs/)
- [PyJavaBridge](https://omena0.dev/PyJavaBridge)
<sub><sup>(Legacy)</sup></sub>
