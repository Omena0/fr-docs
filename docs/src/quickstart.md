# Quickstart

Quick example project setup.

## Step 1: Create a Project

```bash
mkdir my-project
cd my-project

uv venv
uv pip install fr-docs
mkdir docs
```

## Step 2: Create config.json

Create a `config.json` file in `docs/`:

```json
{
  "project_name": "My Project",
  "project_url": "https://github.com/your-org/my-project",
  "docs_dir": ".",
  "site_path_prefix": "/my-project/",
  "sidebar": [
    ["Getting Started", [
      ["getting_started/index", "Home"],
      ["getting_started/quickstart", "Quickstart"]
    ]],
    ["Usage", [
      ["usage/build", "Build"]
    ]]
  ],
  "build": {
    "workers": 6,
    "minify_html": true,
    "optimize_html": true,
    "zstd_level": 22,
    "search_index_filename": "search_index.zst",
    "git_meta_filename": "git_meta.json"
  },
  "versioning": {
    "commit_message_pattern": "^\\s*([0-9]+[A-Za-z])\\s*[-:—–]\\s*(.+)",
    "live_label": "Live"
  }
}
```

### Configuring for different environments

You can use different config files for different environments:

```json
// config.staging.json
{
  "project_name": "My Project (Staging)",
  "project_url": "https://github.com/your-org/my-project",
  "site_path_prefix": "/my-project/",
  "build": {
    "minify_html": false,
    "optimize_html": false
  }
}
```

```json
// config.production.json
{
  "project_name": "My Project",
  "project_url": "https://github.com/your-org/my-project",
  "site_path_prefix": "/my-project/",
  "build": {
    "workers": 8,
    "minify_html": true,
    "optimize_html": true,
    "zstd_level": 22
  }
}
```

Build with specific config:

```bash
# Production build
fr-docs build --production --config config.production.json

# Staging build
fr-docs build --config config.staging.json
```

## Step 3: Add Markdown Files

Create markdown files in the `docs/src/` directory:

```tree
docs/src/
├── getting_started/
│   ├── index.md
│   └── quickstart.md
└── usage/
    └── build.md
```

## Step 4: Build & deploy

Use the action on this repo.

Create `.github/workflows/pages.yml`:

```yml
name: Docs

on:
  push:
    branches: ["main"]
  workflow_dispatch:

permissions:
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Build and Deploy fr-docs Site
        uses: Omena0/fr-docs@1A
```
