#!/usr/bin/env python3
"""
Build script for the fr-docs documentation site.
Converts Markdown source files into a static HTML site using configuration.
"""

import argparse
import concurrent.futures
import json
import logging
import os
import shutil
import sys
from pathlib import Path

import zstandard

from .config import load_config
from .config_accessors import (
    out_dir,
    project_name,
    search_index_filename,
    sidebar,
    src_dir,
    workers,
    zstd_level,
)
from .git import collect_git_metadata, write_git_metadata, build_version_options
from .html_pipeline import build_page
from .search import build_search_index
from .slug import (
    build_slug_page_keys,
    slug_output_name,
)
from .utils import normalized_site_prefix


def main(argv=None):
    if argv is not None and argv and argv[0] == "build":
        argv = argv[1:]
    elif argv is None:
        if (
            Path(sys.argv[0]).name == "fr-docs"
            and len(sys.argv) > 1
            and sys.argv[1] == "build"
        ):
            sys.argv.pop(1)
            argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Build the fr-docs documentation site."
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Rewrite internal links to site-root absolute paths for deployed docs.",
    )
    parser.add_argument(
        "--config",
        help="Path to the configuration JSON file.",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    config["production"] = bool(args.production)

    print(f"📖 Building {project_name(config)} docs...")
    print(f"   Source: {src_dir(config)}")
    print(f"   Output: {out_dir(config)}")
    print(f"   Mode: {'production' if args.production else 'development'}")
    if args.production:
        print(f"   Site prefix: {normalized_site_prefix(config)}")
    print()

    # Copy static assets
    docs_path = Path(config["_docs_dir"])
    for name in ("favicon.svg", "script.js", "style.css"):
        src = docs_path / name
        dst = Path(config["_out_dir"]) / name

        try:
            shutil.copyfile(src, dst)
        except FileNotFoundError:
            pass
        except OSError as e:
            pass

    slugs = get_all_slugs(config)

    # Also check for any .md files not in the sidebar
    if os.path.isdir(config["_src_dir"]):
        for dirpath, _dirnames, filenames in os.walk(config["_src_dir"]):
            for fname in filenames:
                if fname.endswith(".md"):
                    rel = os.path.relpath(
                        os.path.join(dirpath, fname), config["_src_dir"]
                    )
                    s = rel[:-3]
                    if s not in slugs:
                        slugs.append(s)

    config["_slug_page_keys"] = build_slug_page_keys(slugs)

    # Build search index
    search_index = build_search_index(slugs, config)

    # Compress search index
    search_json = json.dumps(search_index, separators=(",", ":"))
    cctx = zstandard.ZstdCompressor(level=zstd_level(config))
    compressed = cctx.compress(search_json.encode("utf-8"))
    search_index_path = os.path.join(config["_out_dir"], search_index_filename(config))
    os.makedirs(os.path.dirname(search_index_path), exist_ok=True)
    with open(search_index_path, "wb") as sf:
        sf.write(compressed)

    if args.production:
        config["_search_index_inline"] = ""
    else:
        import base64

        config["_search_index_inline"] = (
            '<script id="zstd-data" type="text/plain">'
            f"{base64.b64encode(compressed).decode('ascii')}"
            "</script>"
        )

    print(
        f"   Search index: {len(search_json.encode('utf-8')):,} bytes → {len(compressed):,} zstd ({100 * len(compressed) / len(search_json.encode('utf-8')):.1f}%)"
    )

    # Git metadata
    git_meta = collect_git_metadata(config)
    write_git_metadata(git_meta, config)

    # Build version options
    build_version_options(git_meta, config)

    built = 0

    # Build pages
    slugs_to_build = []
    for slug in slugs:
        src = os.path.join(config["_src_dir"], f"{slug}.md")
        if os.path.exists(src):
            slugs_to_build.append(slug)

    if slugs_to_build:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=workers(config)
        ) as executor:
            future_to_slug = {
                executor.submit(build_page, slug, config, config["_slug_page_keys"]): slug
                for slug in slugs_to_build
            }
            for fut in concurrent.futures.as_completed(future_to_slug):
                slug = future_to_slug[fut]
                try:
                    fut.result()
                    print(f"  ✓ {slug_output_name(slug, config)}")
                    built += 1
                except Exception as e:
                    print(f"  ✗ {slug_output_name(slug, config)} (error: {e})")
    else:
        print("No pages found to build.")

    print(f"\n✅ Built {built} pages")


def get_all_slugs(config):
    """Get all markdown file slugs from the sidebar definition."""
    slugs = []
    for _, pages in sidebar(config):
        slugs.extend(slug for slug, _ in pages)

    return slugs


if __name__ == "__main__":
    main()