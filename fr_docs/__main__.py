"""Entry point for fr-docs CLI.

Usage:
    python -m fr_docs build [--production] [--symlink] [--config CONFIG]
    fr-docs build [--production] [--symlink] [--config CONFIG]
    python -m fr_docs init [DIR] [config|fonts]
    fr-docs init [DIR] [config|fonts]
"""

import argparse
import sys

from .build import main as build_main
from .init import main as init_main


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="fr-docs",
        description="Fast static documentation generator",
    )
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
    )

    # Build command
    build_parser = subparsers.add_parser(
        "build",
        help="Build the documentation site",
    )
    build_parser.add_argument(
        "--production",
        action="store_true",
        help="Rewrite internal links to site-root absolute paths for deployed docs.",
    )
    build_parser.add_argument(
        "--symlink",
        action="store_true",
        help=(
            "Create a {site_prefix}/ symlink dir under site/ so a local "
            "production build can be opened in a browser. Off by default: "
            "in CI the whole docs/site/ tree is deployed as-is, and a nested "
            "fr-docs/ symlink folder would show up as "
            "omena0.dev/fr-docs/fr-docs/."
        ),
    )
    build_parser.add_argument(
        "--config",
        help="Path to the configuration JSON file.",
    )

    # Init command
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize a new documentation project",
    )
    init_parser.add_argument(
        "dir",
        nargs="?",
        default="docs",
        help="Directory to initialize (default: docs)",
    )
    init_parser.add_argument(
        "target",
        nargs="?",
        choices=["config", "fonts"],
        default=None,
        help="Initialize only the configuration or download fonts.",
    )

    args = parser.parse_args(sys.argv[1:])

    if args.command == "build":
        build_argv: list[str] = []

        if args.production:
            build_argv.append("--production")

        if args.symlink:
            build_argv.append("--symlink")

        if args.config:
            build_argv.extend(["--config", args.config])

        build_main(build_argv)
        return

    if args.command == "init":
        # If first arg is "config" or "fonts" with no explicit dir, use current directory
        if args.dir in ("config", "fonts") and args.target is None:
            init_main(".", args.dir)
            return

        init_main(args.dir, args.target)
        return

    # Default to build for backwards compatibility.
    if len(sys.argv) > 1 and sys.argv[1] in (
        "--production",
        "--symlink",
        "--config",
        "--help",
        "-h",
    ):
        build_main(sys.argv[1:])
        return

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()