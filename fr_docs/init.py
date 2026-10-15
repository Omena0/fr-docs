"""Initialize a new fr-docs documentation project."""

import json
import platform
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

DEFAULT_CONFIG = {
    "$schema": "https://raw.githubusercontent.com/Omena0/fr-docs/main/config.schema.json",
    "project_name": "My Project",
    "copyright_holder": "CHANGE_ME",
    "project_url": "",
    "site_path_prefix": "/",
    "src_dir": "src",
    "out_dir": "site",
    "docs_dir": ".",
    "sidebar": [
        [
            "Getting Started",
            [
                ["index", "Home"],
                ["installation", "Installation"],
                ["quickstart", "Quickstart"],
                ["configuration", "Configuration"],
            ],
        ]
    ],
    "build": {
        "workers": 6,
        "minify_html": True,
        "optimize_html": True,
        "zstd_level": 22,
        "search_index_filename": "search_index.zst",
        "git_meta_filename": "git_meta.zst",
    },
    "versioning": {
        "commit_message_pattern": r"^\s*([0-9]+[A-Za-z])\s*[-:—–]\s*(.+)",
        "live_label": "Live",
    },
    "source_files": {
        "search_dirs": ["parent", "src_parent", "docs"],
        "patterns": ["docs/src/*.md", "docs/*.js", "docs/*.css"],
        "ignore_dirs": [],
    },
    "features": {
        "backlinks": True,
        "related": True,
        "auto_link": True,
        "versioning": True,
        "search": True,
        "code_references": True,
        "link_preview": True,
        "code_highlighting": True,
        "blockquotes": True,
        "ext_tags": True,
        "inline_copy": True,
    },
}

DEFAULT_INDEX_MD = """# Welcome to {project_name}

{project_name} documentation built with fr-docs.

## Quick Links

- [Installation](installation.md)
- [Quickstart](quickstart.md)
- [Configuration](configuration.md)

## Getting Started

See the [Quickstart](quickstart.md) guide to get up and running quickly.

## Features

- **Fast**: Parallel builds with incremental caching
- **Search**: Full-text search with compressed index
- **Versioning**: Automatic versioning from git history
- **Customizable**: Configure everything via config.json
"""

DEFAULT_INSTALLATION_MD = """# Installation

## Prerequisites

- Python >= 3.10
- pip

## Install from PyPI

```bash
pip install fr-docs
```

## Install from Source

```bash
git clone https://github.com/Omena0/fr-docs.git
cd fr-docs
pip install -e .
```

## Project Setup

1. Create a `config.json` in `docs/`
2. Add your documentation markdown files in `docs/src/`
3. Run `fr-docs build`
4. Serve files in `docs/site/`
"""

DEFAULT_QUICKSTART_MD = """# Quickstart

## 1. Initialize your docs

```bash
fr-docs init
```

This creates a `docs/` directory with sample configuration and content.

## 2. Edit your configuration

Open `docs/config.json` and customize:
- `project_name`: Your project name
- `project_url`: Your project repository URL
- `sidebar`: Navigation structure

## 3. Write your documentation

Add markdown files to `docs/src/` following the sidebar structure.

## 4. Build your docs

```bash
fr-docs build
```

The output will be in `docs/site/`.

## 5. Preview locally

```bash
cd docs/site && python -m http.server 8000
```

Then open http://localhost:8000

## 6. Deploy

Upload the `docs/site/` directory to your hosting provider (Netlify, Vercel, GitHub Pages, etc.)
"""

DEFAULT_CONFIGURATION_MD = """# Configuration

## Configuration File

Create a `config.json` in your docs directory:

```json
{
  "project_name": "My Project",
  "project_url": "https://github.com/user/repo",
  "site_path_prefix": "/",
  "src_dir": "src",
  "out_dir": "site",
  "docs_dir": ".",
  "sidebar": [
    ["Getting Started", [
      ["index", "Home"],
      ["installation", "Installation"]
    ]]
  ],
  "source_files": {
    "search_dirs": ["parent", "src_parent", "docs"],
    "patterns": [
      "docs/src/*.md",
      "docs/*.js",
      "docs/*.css"
    ],
    "ignore_dirs": []
  }
}
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `project_name` | string | "Project Name" | Display name for your project |
| `project_url` | string | "" | Project repository URL |
| `site_path_prefix` | string | "/" | URL path prefix for deployment |
| `src_dir` | string | "src" | Source markdown directory |
| `out_dir` | string | "site" | Output HTML directory |
| `docs_dir` | string | "." | Docs root directory |
| `sidebar` | array | [] | Navigation structure |
| `source_files.patterns` | array | ["docs/src/*.md", "docs/*.js", "docs/*.css"] | Glob patterns for source files (see note below) |
| `source_files.ignore_dirs` | array | [] | Directory names to skip |

## Build Options

```json
{
  "build": {
    "workers": 6,
    "minify_html": true,
    "optimize_html": true,
    "zstd_level": 22,
    "search_index_filename": "search_index.zst",
    "git_meta_filename": "git_meta.json"
  }
}
```

## Feature Toggles

```json
{
  "features": {
    "backlinks": true,
    "related": true,
    "auto_link": true,
    "versioning": true,
    "search": true,
    "code_references": true,
    "link_preview": true,
    "code_highlighting": true,
    "blockquotes": true,
    "ext_tags": true
  }
}
```

## Versioning

```json
{
  "versioning": {
    "commit_message_pattern": "^\\\\s*([0-9]+[A-Za-z])\\\\s*[-:—–]\\\\s*(.+)",
    "live_label": "Live"
  }
}
```

## Source Files

The `source_files` configuration controls which files are indexed for code references and search:

- `patterns`: Glob patterns (relative to each search directory). Use `*` for any filename, `**` for recursive.
- `search_dirs`: Where to search. Options: `"parent"` (project root), `"src_parent"`, `"docs"`.
- `ignore_dirs`: Directory names to skip during search.

Add your own patterns to `patterns` to include additional file types or directories.
"""

SCRIPT_JS_URL = (
    "https://raw.githubusercontent.com/Omena0/fr-docs/refs/heads/main/docs/script.js"
)
STYLE_CSS_URL = (
    "https://raw.githubusercontent.com/Omena0/fr-docs/refs/heads/main/docs/style.css"
)
FAVICON_SVG_URL = (
    "https://raw.githubusercontent.com/Omena0/fr-docs/refs/heads/main/docs/favicon.svg"
)

GITHUB_WORKFLOW_YML = """name: Docs

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
        with:
          fetch-depth: 0
      - name: Build and Deploy fr-docs Site
        uses: Omena0/fr-docs@main
"""

DEFAULT_CSS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Inter:ital,opsz,wght@0,14..32,400..800"
    "&family=JetBrains+Mono:wght@400..700&display=swap"
)

FONT_FACE_RE = re.compile(
    r"@font-face\s*\{\n"
    r"\s*font-family:\s*['\"](?P<family>[^'\"]+)['\"]\s*;\n"
    r"\s*font-style:\s*(?P<style>\w+)\s*;\n"
    r"\s*font-weight:\s*(?P<weight>\d+)\s*;\n"
    r"\s*font-display:\s*(?P<display>\w+)\s*;\n"
    r"\s*src:\s*url\((?P<src>[^)]+)\)\s*format\(['\"](?P<format>[^'\"]+)['\"]\)\s*;\n"
    r"\}"
)

METRICS = {
    "Inter": "1984 494",
    "JetBrains Mono": "1020 300",
}


def download_file(url, dest_path) -> bool:
    """Download a file from URL to dest_path."""
    try:
        print(f"  Downloading {url}...")
        req = urllib.request.Request(url, headers={"User-Agent": "fr-docs/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read()
        dest_path.write_bytes(content)
        print(f"  ✓ Saved to {dest_path}")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  ✗ Failed to download {url}: {e}")
        return False


def fetch_fonts_css(css_url: str) -> str:
    """Fetch Google Fonts CSS text."""
    req = urllib.request.Request(css_url, headers={"User-Agent": "fr-docs/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def download_font(url: str, dest: Path) -> bool:
    """Download a single font file."""
    if dest.exists() and dest.stat().st_size > 0:
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "fr-docs/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        if len(data) < 1000:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  ! failed to download {url}: {exc}", file=sys.stderr)
        return False


def run_fetch_fonts(docs_dir: Path, css_url: str = DEFAULT_CSS_URL) -> int:
    """Download Google Fonts and generate local fonts.css."""
    out_dir = docs_dir / "fonts"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching Google Fonts CSS from {css_url}")
    css = fetch_fonts_css(css_url)

    faces = FONT_FACE_RE.findall(css)
    if not faces:
        print("ERROR: no @font-face blocks found in CSS", file=sys.stderr)
        return 1

    print(f"Found {len(faces)} font-face rules")

    local_rules = []
    for family, style, weight, _display, src_url, fmt in faces:
        src_url = src_url.strip().strip("'\"")
        fname = Path(src_url.split("?")[0]).name
        if not fname:
            continue
        dest = out_dir / fname
        print(f"  {family} {weight} {style} -> {fname}")
        if not download_font(src_url, dest):
            print(f"  ! skipping {family} {weight} {style} (download failed)")
            continue
        if metrics := METRICS.get(family, ""):
            local_rules.append(
                f"""@font-face {{
  font-family: '{family}';
  font-style: {style};
  font-weight: {weight};
  font-display: swap;
  src: url('fonts/{fname}') format('{fmt}');
  font-ascent-descent: {metrics};
}}"""
            )
        else:
            local_rules.append(
                f"""@font-face {{
  font-family: '{family}';
  font-style: {style};
  font-weight: {weight};
  font-display: swap;
  src: url('fonts/{fname}') format('{fmt}');
}}"""
            )

    if not local_rules:
        print("ERROR: no fonts were downloaded", file=sys.stderr)
        return 1

    fonts_css = "\n".join(local_rules) + "\n"
    css_out = docs_dir / "fonts.css"
    css_out.write_text(fonts_css, encoding="utf-8")
    print(f"\nWrote {len(local_rules)} font-face rules to {css_out}")
    return 0


def create_uv_venv(docs_dir) -> None:
    """Create a uv virtual environment on Linux if uv is installed."""
    if platform.system() != "Linux":
        return

    if not shutil.which("uv"):
        return

    venv_path = docs_dir / ".venv"
    if venv_path.exists():
        print(f"  ⊘ Virtual environment already exists at {venv_path}")
        return

    try:
        print("  Creating uv virtual environment...")
        result = subprocess.run(
            ["uv", "venv", str(venv_path)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if result.returncode == 0:
            print(f"  ✓ Created virtual environment at {venv_path}")
        else:
            print(f"  ✗ Failed to create virtual environment: {result.stderr}")
    except Exception as e:  # noqa: BLE001
        print(f"  ✗ Failed to create virtual environment: {e}")


def create_github_workflow(docs_dir) -> None:
    """Create .github/workflows/pages.yml for GitHub Pages deployment."""
    workflow_dir = docs_dir.parent / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    workflow_path = workflow_dir / "pages.yml"

    if workflow_path.exists():
        print(f"  ⊘ GitHub workflow already exists at {workflow_path}")
        return

    try:
        workflow_path.write_text(GITHUB_WORKFLOW_YML, encoding="utf-8")
        print(f"  ✓ Created GitHub Pages workflow at {workflow_path}")
    except Exception as e:  # noqa: BLE001
        print(f"  ✗ Failed to create GitHub workflow: {e}")


def src_dir_has_content(src_dir: Path) -> bool:
    """Check if src directory has any files or folders."""
    if not src_dir.exists():
        return False
    try:
        return any(src_dir.iterdir())
    except OSError:
        return False


def create_default_files(docs_dir: Path, project_name: str) -> None:
    """Create default markdown files in src directory, but only if src is empty."""
    src_dir = docs_dir / "src"

    if src_dir_has_content(src_dir):
        print(f"  ⊘ {src_dir} already has content, skipping default markdown files")
        return

    src_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "index.md": DEFAULT_INDEX_MD.format(project_name=project_name),
        "installation.md": DEFAULT_INSTALLATION_MD,
        "quickstart.md": DEFAULT_QUICKSTART_MD,
        "configuration.md": DEFAULT_CONFIGURATION_MD,
    }

    for filename, content in files.items():
        filepath = src_dir / filename
        filepath.write_text(content, encoding="utf-8")
        print(f"  ✓ Created {filepath}")


def create_config_only(docs_dir: Path) -> None:
    """Create only config.json in the specified directory."""
    docs_dir = docs_dir.resolve()
    docs_dir.mkdir(parents=True, exist_ok=True)

    config_path = docs_dir / "config.json"
    if config_path.exists():
        print(f"  ⊘ {config_path} already exists, not overwriting")
        return

    config = DEFAULT_CONFIG.copy()
    config["project_name"] = docs_dir.name.replace("-", " ").replace("_", " ").title()
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print(f"  ✓ Created {config_path}")


def create_full_init(docs_dir: Path) -> None:
    """Create a full documentation project with config, markdown, assets, and workflow."""
    docs_dir = docs_dir.resolve()

    print(f"📁 Initializing fr-docs project in {docs_dir}")

    # Create directories
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "src").mkdir(parents=True, exist_ok=True)

    # Create config.json
    config_path = docs_dir / "config.json"
    config = DEFAULT_CONFIG.copy()
    config["project_name"] = docs_dir.name.replace("-", " ").replace("_", " ").title()
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print(f"  ✓ Created {config_path}")

    # Create default markdown files (only if src is empty)
    project_name = str(config["project_name"])
    create_default_files(docs_dir, project_name)

    # Download static assets
    print("📥 Downloading static assets...")
    download_file(SCRIPT_JS_URL, docs_dir / "script.js")
    download_file(STYLE_CSS_URL, docs_dir / "style.css")
    download_file(FAVICON_SVG_URL, docs_dir / "favicon.svg")

    # Create uv virtual environment on Linux
    print("🔧 Setting up development environment...")
    create_uv_venv(docs_dir)

    # Create GitHub Pages workflow
    print("📝 Creating GitHub Pages workflow...")
    create_github_workflow(docs_dir)

    print()
    print("✅ Documentation project initialized!")
    print()
    print("Next steps:")
    print(f"  1. Edit {config_path} to customize your project")
    print(f"  2. Add markdown files to {docs_dir}/src/")
    print("  3. Run 'fr-docs build' to generate your site")
    print(f"  4. Preview with 'cd {docs_dir}/site && python -m http.server 8000'")


def main(docs_dir_str="docs", target=None) -> None:
    """Initialize a new documentation project.

    Args:
        docs_dir_str: Directory to initialize (default: "docs")
        target: One of None (full init), "config" (config only), "fonts" (download fonts)
    """
    docs_dir = Path(docs_dir_str).resolve()

    if target == "config":
        print(f"📁 Creating config.json in {docs_dir}")
        create_config_only(docs_dir)
        return

    if target == "fonts":
        print(f"📁 Downloading fonts in {docs_dir}")
        sys.exit(run_fetch_fonts(docs_dir))

    # Full init
    create_full_init(docs_dir)


if __name__ == "__main__":
    # Support legacy: fr-docs init [dir] [config]
    # New: fr-docs init [dir] [config|fonts]
    if len(sys.argv) > 2 and sys.argv[2] in ("config", "fonts"):
        main(sys.argv[1], sys.argv[2])
    elif len(sys.argv) > 1 and sys.argv[1] in ("config", "fonts"):
        main("docs", sys.argv[1])
    else:
        main(sys.argv[1] if len(sys.argv) > 1 else "docs")