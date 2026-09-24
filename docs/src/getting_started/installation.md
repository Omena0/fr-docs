# Installation

## Prerequisites

- Python >= 3.14
- pip

## Install from PyPI

```bash
pip install fr-docs
```

## Install from Source

```bash
git clone https://github.com/your-org/fr-docs.git
cd fr-docs
pip install --no-deps -e .
```

## Project Setup

1. Create a `config.json` in your project root
2. Add your documentation markdown files in `src/`
3. Run `fr-docs build`

## Dependencies

Install build dependencies:

```bash
pip install markdown zstandard
```

Or install as a package dependency in your `pyproject.toml`:

```toml
dependencies = [
    "fr-docs",
]
```
