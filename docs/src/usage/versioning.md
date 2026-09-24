# Versioning

Fr-docs supports semantic versioning based on commit messages.

## Commit Message Format

Use the format:

```text
<version> - <description>
```

Where `<version>` follows the pattern:

```text
<MAJOR><LETTER>
```

## Examples

| Commit Message | Version |
|----------------|---------|
| `0A - Initial release` | `0.1.0` |
| `0B - Add search` | `0.2.0` |
| `4D - Fix bug` | `4.4.0` |
| `4D1 - Patch fix` | `4.4.1` |

## How It Works

The versioning system:
1. Parses commit messages
2. Extracts the version code
3. Converts it to semantic version
4. Creates versioned URLs and releases

## Configuration

```json
{
  "versioning": {
    "commit_message_pattern": "^\\s*([0-9]+[A-Za-z])\\s*[-:—–]\\s*(.+)",
    "live_label": "Live"
  }
}
```

## Live Label

The `live_label` field controls the label shown for the latest version:

```json
{
  "versioning": {
    "live_label": "Live"
  }
}
```

You can change it to "Stable", "Release", etc.
