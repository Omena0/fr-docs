# Installation

How to install and set up fr-docs.

## Prerequisites

- Python >= 3.14
- pip

## Install from PyPI

### Standard installation

```bash
pip install fr-docs
```

### Install in a virtual environment

```bash
uv venv
uv pip install fr-docs
```

### Install a specific version

```bash
pip install fr-docs==1.0.0
```

## Install from Source

### Clone and install

```bash
git clone https://github.com/Omena0/fr-docs.git
cd fr-docs
pip install -e .
```

## Project Setup

1. Create a `config.json` in `docs/`
2. Add your documentation markdown files in `docs/src/`
3. Run c`fr-docs build`
4. Serve files in `docs/site`

### Project structure example

```tree
my-project/
├── my_module/
├── docs/
│   ├── src/
│   │   └── index.md
│   └── config.json
└── pyproject.toml
```

## Verify Installation

```bash
fr-docs --help
```

Expected output should show the available commands and options.

## Upgrade

```bash
pip install --upgrade fr-docs
```

## Uninstall

```bash
pip uninstall fr-docs
```
