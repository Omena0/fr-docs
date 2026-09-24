# Version Format

## Format

The version format is:

```text
<MAJOR><LETTER>
```

Where:
- `MAJOR` is a number
- `LETTER` is a letter from A-Z
- The letter is converted to a number (A=1, B=2, C=3, D=4, etc.)

## Examples

| Code | Semantic Version |
|------|-----------------|
| `0A` | `0.1.0` |
| `0B` | `0.2.0` |
| `0Z` | `0.26.0` |
| `4D` | `4.4.0` |
| `4D1` | `4.4.1` |

## Conversion

The conversion is done by taking the letter's ASCII value and subtracting 96:

```python
letter = "D"
minor = ord(letter) - 96  # 68 - 96 = 4
```

## Patch Versions

Patch versions are appended directly to the code:

```text
4D1 = 4.4.1
4D2 = 4.4.2
```

## Commit Messages

Use the format:

```text
4D - Fix bug
4D1 - Patch fix
```

The versioning system will automatically detect and convert these to semantic versions.