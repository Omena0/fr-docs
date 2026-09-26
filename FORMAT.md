
# Formatting guide

This is this project's own style — not PEP 8, not Black. `~/GitHub/fr-db/fr_db/types/index.py` is the reference file; read along with it. When in doubt, match `index.py`.

## Empty lines (most important)

The placement of blank lines is the single biggest signal of how a file reads.

### Top level

- The file is split into top-level **blocks**: the imports section, the definitions section, and a trailing `__main__` section.
- **2 blank lines** separate top-level blocks (e.g. imports ↔ first definition, last definition ↔ `__main__`).
- **1 blank line** between consecutive top-level functions/classes and between top-level statements.

```python
from fr_db.types.column import Column
from fr_db.types.rowview import RowView
from fr_db.types.table import Table


class TableView(Table): ...
```

### Imports

- **1 blank line** between import groups. `from __future__ import annotations` is its own group at the very top (Python requires it first), then a blank line, then the rest.

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .table import Table
    from .row import Row
```

### Between class members

- **Exactly 1 blank line** between methods, including between dunder methods and between methods that share a category.
- A category comment (e.g. `# Internal`, `# Properties`, `# Index operations`, `# Lifecycle`) gets **1 blank line before** it and **no blank line after** it — the first member of the category follows immediately.

```python
    def __repr__(self) -> str:
        ...
                              # <- 1 blank line
    # Lifecycle                # <- comment, no blank after this
    def build(self, table: Table) -> None:
```

### Inside method bodies (block separation)

- A method body is a series of **blocks** ("paragraphs") of related statements at the same indent. **1 blank line between blocks**; keep related statements together in one block (no blank line).
- Target ~2-4 statements per block; the goal is to separate each logical step, not to pad.

```python
def _ensure_built(self) -> None:
    ...
    if not self._dirty:  # block 1
        return

    self._dirty = False  # block 2
    self._values.clear()
    self._shared = False

    table = self._table  # block 3
    ...
```

- Tightly coupled statements stay in one block. A mutation immediately followed by a check on its result is one block: no blank line.

```python
            else:
                ids.remove(row.id)
                if not ids:
                    del self._values[value]
```

### Inside `if` / `elif` / `else`

- Each branch is a block: **1 blank line between branches** (when branches are multi-statement).

```python
        if ids is None:
            self._values[value] = {row_id}

        elif self._shared:
            ids = ids.copy()
            ids.add(row_id)

            self._values[value] = ids

        else:
            ids.add(row_id)
```

### Comments inside method bodies

- A comment attaches to the statement that follows it. **1 blank line before** the comment, **no blank line between** the comment and the statement it describes.

```python
        # Phase 1: Fuse compatible operations
        result = cls._fuse_ops(ops)

        # Phase 2: Merge consecutive same-type operations
        result = cls._merge_consecutive(result)
```

- Trailing inline comments are separated from the preceding code by **one space**.

```python
        for row_id, row in table._rows.items(): # pyright: ignore[reportPrivateUsage]
```

### File ending

- End the file with **exactly 2 blank lines** after the last statement.

## Indentation

- 4 spaces. No tabs.
- **No hanging indent** for function signatures, call arguments, and comprehensions: the opening `(`, `[`, or `{` ends the line with nothing after it.
Arguments/elements indent **one level (4 spaces) deeper** than the line holding the opening delimiter; the closing delimiter aligns with the opening line.

```python
    def update(
        self,
        old_value: Any,
        new_value: Any,
        row_id: int,
    ) -> None:
```

```python
raise ValueError(f"Duplicate value {value!r} for unique index {self.column!r}")
```

## Multiline function signatures

- There is **no hard line-length limit**. Break a signature onto multiple lines only when it genuinely feels too long, judging by argument count, annotation length, defaults, and width. When it is short enough, keep it on one line.
- When breaking: first argument one level deeper than `def`; closing `) -> ret:` aligned with `def`; **trailing comma** after the last argument is **optional**.

```python
    def update(
        self,
        old_value: Any,
        new_value: Any,
        row_id: int,
    ) -> None:
```

## Multi-line boolean conditions (`if` / `while`)

- This is the one place content may follow the opening `(`.
- Preferred (when the conditions are similar and `if (` is short): put the first operand on the `if (` line and align the following operands under it; closing `):` at the end of the last line.

```python
if (op.type == OpType.WHERE and i + 2 < n
    and ops[i + 1].type == OpType.TRANSFORM
    and ops[i + 2].type == OpType.SELECT):
```

- If the aligned style is awkward (`elif`, dissimilar / very long conditions), go full multiline instead: `(` on its own line, operands one level deeper than the statement, `):` on its own line aligned with the statement.

```python
elif (
    op.type == OpType.WHERE and i + 2 < n
    and ops[i + 1].type == OpType.TRANSFORM
    and ops[i + 2].type == OpType.SELECT
):
```

## Multiline calls

- Args one level deeper than the opening line; closing `)` aligned with the opening line.
- Adjacent string literals are implicitly concatenated; put the trailing space **inside** the string (`f"... "`) when the join point needs a space.

```python
raise ValueError(f"Duplicate value {value!r} for unique index {self.column!r}")
```

## Comprehensions

- Opening `{` stays on the assignment line. `key: value` on its own line, one level deeper than the assignment; `for` / `if` clauses on following lines at the same indent; closing `}` aligned with the assignment.

```python
index._values = {value: ids.copy() for value, ids in self._values.items()}
```

## Classes

Order of members:

1. `__slots__`
2. `__init__`
3. Other dunder methods (`__repr__`, ...)
4. `_`-prefixed private methods, under a category comment (`# Internal`)
5. Properties and setters
6. Public methods, grouped under category comments (e.g. `# Properties`, `# Index operations`, `# Lifecycle`)

- Properties and setters come **after** private methods and **before** public methods. Use a `# Properties` category comment (or `# Internal` for private, `# Query` / `# Mutation` etc. for public).
- Dunder methods (`__init__`, `__repr__`, `__getitem__`, `__str__`, etc.) do **not** get docstrings.
- Members within a category are **not** sorted alphabetically — order them logically. Every non-dunder method has a docstring and its arguments are type-annotated.

### `__slots__`

- A **tuple** of quoted strings, in development order (the order attributes are set up), **not** sorted. No type annotation.

```python
__slots__ = ("_base", "_delta", "_deleted", "_len")
```

- Keep on a single line while it fits (roughly ≤ ~100 chars). When it gets too long, wrap to one name per line; if it is only barely over the limit, the names may share a single line inside the parentheses. No trailing comma.

```python
__slots__ = (
    "database",
    "name",
    "_rows",
    "_columns",
    "indexes",
    "_transaction",
    "operations",
    "_default_columns",
    "_in_transaction",
    "_query_cache",
)
```

### `__all__`

- Always multiline, one item per line, single-quoted. Closing `]` aligned with `__all__`. Trailing comma optional (omit it).

Definition / development order, if it doesnt exist, order by order which they are defined,
otherwise, just add to the end of the list.

```python
__all__ = [
    "Database",
    "Table",
    "TableView",
]
```

## Docstrings

- **Arguments are type-annotated; docstrings are present on every non-dunder method.** Dunder methods (`__init__`, `__repr__`, `__getitem__`, `__str__`, etc.) do **not** get docstrings.
- Body content is indented **one level (4 spaces) deeper** than the opening `""`. The closing `"""` sits on its own line aligned with the opening `"""`.
- Every docstring's first line ends with `\n` (literal backslash-n) to create a blank line after the summary in rendered output.
- **Summary + params** (the common case for methods with parameters): summary ending with `\n` on the opening `"""` line, then `:param:` / `:type:` / `:raises:` / `:return:` / `:rtype:` fields one level deeper.

```python
def __init__(self, column: str, unique: bool = False):
    """Initialize an index on the given column.\n
    :param column: The column name to index
    :type column: str
    :param unique: Whether the index enforces uniqueness
    :type unique: bool
    """
```

- **Summary + description** (methods with no parameters, just prose): summary on the opening `"""` line, a blank line, then the description at the **opening `"` indent** (not deeper); closing `"""` aligned with the opening.

```python
    def get_index(self, column: str) -> Index | None:
        """Return the index associated with a column, or None if no index exists.\n

        Used by lookup helpers to determine whether an indexed lookup is
        available for the requested column.
        """
```

- **Class docstrings** (no params): opening `"""` on its own line, summary/description one level deeper; closing `"""` aligned with the opening.

```python
"""
Index for fast lookups on a column.
Supports unique constraints and lazy rebuilding.
"""
```

- **Summary + params + description** (rare): summary + params (params one level deeper), blank line, description at the opening `"` indent, closing aligned.
A docstring with only a summary is `"""Mark index as needing rebuild.\\n\n"""`.

## Typing

- Strict (pyright/pylance). Use builtin generics (`dict`, `list`, `set`) and modern unions (`Table | None`) — never `typing.Dict` / `List` / `Optional`.
- Type-hint every argument (except `self`). Return annotations are **optional**; omit `-> None` where it adds nothing (it is implied).
- Prefer **specific** suppressions inline and minimal: `# pyright: ignore[reportPrivateUsage]` on the line that touches a private member. A bare `# type: ignore` is acceptable when broadly suppressing (e.g. an `__exit__` dunder whose params you don't want to name).

```python
        for row_id, row in table._rows.items(): # pyright: ignore[reportPrivateUsage]
```

- Import only what is used from `typing`.

## Imports

- Imports are the **only** thing that is sorted: sort **longest to shortest** by line length. `from __future__ import` is always first (Python requirement), then everything else longest-to-shortest.
- Within a single `from X import a, b`, sort the imported names **longest to shortest**.
- Project-internal and type-checking imports go in a separate `if TYPE_CHECKING:` block after the regular imports, with 1 blank line before the block. Inside that block there are **no blank lines** between imports, sorted longest-to-shortest.

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .table import Table
    from .row import Row
```

- Don't alias imports to dodge a name clash — put the import under `TYPE_CHECKING` instead (avoids shadowing at runtime).

## `@overload`

- Stub bodies are `...` on the signature line. No blank lines between overloads, and no blank line before the real implementation — unless an overload is multiline, in which case add a blank line to keep them separated.

```python
    @overload
    def where(self, column: Callable[[Row], bool]) -> TableView: ...
    @overload
    def where(self, column: str, key: Any) -> TableView: ...
    def where(self, column: str | Callable[[Row], bool], key: Any = _MISSING) -> TableView:
```

## Names and annotations

- Class names: `UpperCamelCase`. Functions / methods / variables: `lower_snake_case`. These are recommendations, not absolute.
- Variable annotations: a space after the colon — `self._values: dict[Any, set[int]] = {}`.
- Shadowing a builtin with a local/attribute name (e.g. `id`) is fine as long as the builtin isn't used in that scope.

## Enums

- Enum members: no blank lines between them.

```python
class OpType(IntEnum):
    WHERE = auto()
    TRANSFORM = auto()
    TRANSFORM_ROWS = auto()
```

## Modules

- Split code into distinct files and subfolders; do not put everything in one folder.
- `__main__` should contain nothing except CLI. If it grows past ~50 lines, move the logic to `cli.py` and call it from `__main__`.
