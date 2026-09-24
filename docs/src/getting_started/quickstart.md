# Quickstart

## Step 1: Create a Project

```bash
mkdir my-project
cd my-project
pip install fr-docs
```

## Step 2: Create config.json

Create a `config.json` file in your project root:

```json
{
  "project_name": "My Project",
  "project_url": "https://github.com/your-org/my-project",
  "site_path_prefix": "/my-project/",
  "sidebar": [
    ["Getting Started", [
      ["getting_started/index", "Home"],
      ["getting_started/quickstart", "Quickstart"]
    ]],
    ["Usage", [
      ["usage/build", "Build"]
    ]]
  ]
}
```

## Step 3: Add Markdown Files

Create markdown files in the `docs/src/` directory:

```
docs/src/
├── getting_started/
│   ├── index.md
│   └── quickstart.md
└── usage/
    └── build.md
```

## Step 4: Build

```bash
fr-docs build
```

This generates a static HTML site in the `docs/site/` directory.

## Step 5: Deploy

Upload the contents of `docs/site/` to your hosting provider, or use GitHub Pages.
