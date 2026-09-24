# Build

## Basic Usage

```bash
fr-docs build
```

## Production Build

```bash
fr-docs build --production
```

## Custom Output Directory

```bash
fr-docs build --output-dir ./dist
```

## Search Configuration

```bash
fr-docs build --search --search-level 5
```

## Resume Build

```bash
fr-docs build --resume
```

## Git Metadata

Fr-docs tracks git information by default. To disable:

```json
{
  "build": {
    "include_git_metadata": false
  }
}
```

## Cache

To use cache:

```bash
fr-docs build --use-cache
```

To clear cache:

```bash
fr-docs build --clear-cache
```
