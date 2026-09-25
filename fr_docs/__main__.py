"""Entry point for fr-docs CLI.

Usage:
    python -m fr_docs build [--production] [--config CONFIG]
    fr-docs build [--production] [--config CONFIG]
    python -m fr_docs init [--dir DIR]
    fr-docs init [--dir DIR]
"""

import argparse
import sys

from .build import main as build_main
from .init import main as init_main


def main():
    parser = argparse.ArgumentParser(
        prog="fr-docs", description="Fast static documentation generator"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Build command
    build_parser = subparsers.add_parser("build", help="Build the documentation site")
    build_parser.add_argument(
        "--production",
        action="store_true",
        help="Rewrite internal links to site-root absolute paths for deployed docs.",
    )
    build_parser.add_argument(
        "--config",
        help="Path to the configuration JSON file.",
    )

    # Init command
    init_parser = subparsers.add_parser(
        "init", help="Initialize a new documentation project"
    )
    init_parser.add_argument(
        "dir",
        nargs="?",
        default="docs",
        help="Directory to initialize (default: docs)",
    )

    # Parse args
    args = parser.parse_args(sys.argv[1:])

    if args.command == "build":
        # Convert namespace to list for build_main
        build_argv = []
        if args.production:
            build_argv.append("--production")
        if args.config:
            build_argv.extend(["--config", args.config])
        build_main(build_argv)
    elif args.command == "init":
        init_main(args.dir)
    else:
        # Default to build for backwards compatibility
        if len(sys.argv) > 1 and sys.argv[1] in (
            "--production",
            "--config",
            "--help",
            "-h",
        ):
            build_main(sys.argv[1:])
        else:
            parser.print_help()
            sys.exit(1)


if __name__ == "__main__":
    main()
