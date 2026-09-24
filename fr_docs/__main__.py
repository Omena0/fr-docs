"""Entry point for fr-docs CLI.

Usage:
    python -m fr_docs build [--production] [--config CONFIG]
    fr-docs build [--production] [--config CONFIG]
"""

import sys

from .build import main

if __name__ == "__main__":
    # If called as `python -m fr_docs build ...`, sys.argv[1] will be "build"
    # If called as `fr-docs build ...`, sys.argv[1] will be "build"
    # If called as `fr-docs ...` (no subcommand), sys.argv[1] will be the flags
    args = sys.argv[1:]
    if args and args[0] == "build":
        args = args[1:]
    main(args)
