# API

## Command Line Interface

### fr-docs build

Build documentation from Markdown files.

```bash
fr-docs build [options]
```

Options:
- `--production` - Build for production (minify, optimize)
- `--output-dir` - Override output directory
- `--search` - Enable search
- `--search-level` - Set search level (1-5)
- `--no-search` - Disable search
- `--resume` - Resume from cache
- `--use-cache` - Use cache
- `--clear-cache` - Clear cache
- `--config` - Specify config file

### fr-docs serve

Serve documentation locally.

```bash
fr-docs serve [options]
```

## Python API

```python
from fr_docs import build

# Build documentation
build.build_docs(config_path="config.json")

# Build a single page
build.build_page("getting_started/index")

# Load configuration
from .config import load_config

config = load_config("config.json")
```

## Module API

```python
import fr_docs

# Package version
print(fr_docs.__version__)
```

## Configuration API

```python
from .config import (
    load_config,
    project_name,
    site_prefix,
    sidebar,
    build_settings,
    versioning_config,
)

config = load_config("config.json")
print(project_name(config))
print(site_prefix(config))
print(sidebar(config))
```

## Build API

```python
from fr_docs import build

# Build all documentation
build.build_docs(config_path="config.json")

# Build with custom config
build.build_docs(config_path="config.json", production=True)

# Build a single page
build.build_page("getting_started/index")
```