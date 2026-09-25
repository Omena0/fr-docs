#!/usr/bin/env python3
"""
Build script for the fr-docs documentation site.
Converts Markdown source files into a static HTML site using configuration.
"""

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import xxhash
import zstandard

from .config import load_config
from .config_accessors import (
    feature_enabled,
    out_dir,
    project_name,
    search_index_filename,
    sidebar,
    src_dir,
    workers,
    zstd_level,
)
from .git import build_version_options, collect_git_metadata
from .html_pipeline import build_page
from .search import build_search_index, search_include_config
from .slug import (
    build_slug_page_keys,
    slug_output_name,
)
from .syntax import highlight_source_lines
from .utils import normalized_site_prefix


def _compute_hash(data: str) -> str:
    """Compute xxhash hash of string data."""
    return xxhash.xxh3_128_hexdigest(data.encode("utf-8"))


def _best_zstd_level(raw: bytes, configured: int) -> int:
    """Pick the zstd compression level that minimizes compressed size.

    Scans levels 1..configured and returns the one producing the smallest
    output, breaking ties toward the lower level so decompression stays
    fast. Level 22 is very slow and rarely beats lower levels on real
    payloads, so this avoids paying for it when it doesn't help.
    """
    if len(raw) < 1024:
        return min(configured, 19)

    best_level, best_size = 1, len(zstandard.ZstdCompressor(level=1).compress(raw))
    for level in range(2, configured + 1):
        size = len(zstandard.ZstdCompressor(level=level).compress(raw))
        if size < best_size:
            best_level, best_size = level, size
    return best_level


def _minify_static_asset(config, src: Path, dst: Path, name: str) -> None:
    """Minify a static asset in-place (JS via terser, CSS via html-minifier).

    Falls back to a plain copy if the minifier is unavailable. CSS is minified
    by wrapping it in a `<style>` tag (html-minifier-next only processes CSS
    embedded in HTML) and stripping the wrapper afterwards.
    """
    repo_root = Path(config["_docs_dir"]).resolve().parent
    node_modules = repo_root / "node_modules"

    if name.endswith(".js"):
        terser_bin = node_modules / ".bin" / "terser"
        cmd = [
            str(terser_bin) if terser_bin.exists() else "npx",
            "--yes" if not terser_bin.exists() else "",
            *(["terser"] if not terser_bin.exists() else []),
            str(src),
            "--compress",
            "warnings=false",
            "--mangle",
            "--output",
            str(dst),
        ]
        cmd = [c for c in cmd if c]
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, cwd=str(repo_root)
        )
        if result.returncode != 0 or not dst.exists() or dst.stat().st_size == 0:
            print(f"  ! minify failed for {name}, copying raw: {result.stderr[-300:]}")
            shutil.copyfile(src, dst)
        return

    # CSS: html-minifier-next only minifies CSS embedded in HTML, so wrap the
    # stylesheet in a <style> tag, minify, then strip the wrapper.
    minifier_bin = node_modules / ".bin" / "html-minifier-next"
    raw_css = src.read_text(encoding="utf-8")
    wrapped = f"<style>{raw_css}</style>"
    wrapper = Path(tempfile.mkstemp(suffix=".html")[1])
    min_out = Path(tempfile.mkstemp(suffix=".html")[1])
    try:
        wrapper.write_text(wrapped, encoding="utf-8")
        cmd = [
            str(minifier_bin) if minifier_bin.exists() else "npx",
            "--yes" if not minifier_bin.exists() else "",
            *(["html-minifier-next"] if not minifier_bin.exists() else ""),
            "--minify-css=true",
            "--remove-comments",
            "--output",
            str(min_out),
            str(wrapper),
        ]
        cmd = [c for c in cmd if c]
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, cwd=str(repo_root)
        )
        if result.returncode == 0 and min_out.exists():
            out = min_out.read_text(encoding="utf-8")
            m = re.search(r"<style>([\s\S]*)</style>", out)
            if m:
                dst.write_text(m.group(1), encoding="utf-8")
                return
        print(f"  ! minify failed for {name}, copying raw: {result.stderr[-300:]}")
    finally:
        try:
            wrapper.unlink()
        except OSError:
            pass
        try:
            min_out.unlink()
        except OSError:
            pass
    shutil.copyfile(src, dst)


class BuildCache:
    """Manage caching of build data to avoid unnecessary regeneration."""

    def __init__(self, cache_path: str):
        self.cache_path = Path(cache_path)
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        """Load the build cache from disk."""
        if not self.cache_path.exists():
            return {}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError, OSError:
            return {}

    def _save_cache(self):
        """Save the build cache to disk."""
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, separators=(",", ":"))

    def needs_regeneration(self, key: str, current_hash: str) -> bool:
        """Check if data needs regeneration based on hash."""
        cached_hash = self.cache.get(key)
        return True if cached_hash is None else cached_hash != current_hash

    def update_cache(self, key: str, new_hash: str):
        """Update cache with new hash."""
        self.cache[key] = new_hash
        self._save_cache()

    def get_cached_path(self, filename: str, out_dir: str) -> Path:
        """Get the path to cached .zst file."""
        return Path(out_dir) / f"{filename}.zst"


def _write_zstd_json(config, filename, value):
    raw = json.dumps(value, separators=(",", ":")).encode("utf-8")
    raw_hash = _compute_hash(raw.decode("utf-8"))
    cache = BuildCache(str(Path(config["_out_dir"]) / ".build_cache.json"))

    if not cache.needs_regeneration(filename, raw_hash):
        src = cache.get_cached_path(filename, config["_out_dir"])
        if src.exists():
            return len(raw), src.stat().st_size

    compressed = zstandard.ZstdCompressor(level=_best_zstd_level(raw, zstd_level(config))).compress(raw)
    path = Path(config["_out_dir"]) / filename
    path.write_bytes(compressed)
    cache.update_cache(filename, raw_hash)
    return len(raw), len(compressed)


def collect_source_files(config):
    """Collect source code files for code reference feature using glob patterns."""
    import glob as glob_module

    source_files = {}
    docs_path = Path(config["_docs_dir"])
    src_dir_path = Path(config["_src_dir"])
    source_config = config.get("source_files", {})

    # Resolve search directories
    search_dirs_raw = source_config.get("search_dirs", ["parent", "src_parent", "docs"])
    search_dirs = []
    for sd in search_dirs_raw:
        if sd == "parent":
            search_dirs.append(docs_path.parent)
        elif sd == "src_parent":
            search_dirs.append(src_dir_path.parent)
        elif sd == "docs":
            search_dirs.append(docs_path)
        elif Path(sd).exists():
            search_dirs.append(Path(sd))

    # Get glob patterns from config
    patterns = source_config.get(
        "patterns",
        [
            "**/*.py",
            "**/*.js",
            "**/*.ts",
            "**/*.tsx",
            "**/*.jsx",
            "**/*.java",
            "**/*.cpp",
            "**/*.c",
            "**/*.h",
            "**/*.hpp",
            "**/*.rs",
            "**/*.go",
            "**/*.rb",
            "**/*.php",
            "**/*.cs",
            "**/*.kt",
            "**/*.swift",
            "**/*.scala",
            "**/*.clj",
            "**/*.hs",
            "**/*.ml",
            "**/*.fs",
            "**/*.vim",
            "**/*.sh",
            "**/*.bash",
            "**/*.zsh",
            "**/*.fish",
            "**/*.ps1",
            "**/*.bat",
            "**/*.cmd",
            "**/*.sql",
            "**/*.html",
            "**/*.htm",
            "**/*.xml",
            "**/*.json",
            "**/*.yaml",
            "**/*.yml",
            "**/*.toml",
            "**/*.ini",
            "**/*.cfg",
            "**/*.conf",
            "**/*.md",
            "**/*.txt",
            "**/*.rst",
            "**/*.css",
            "**/*.scss",
            "**/*.sass",
            "**/*.less",
            "**/*.styl",
            "**/*.vue",
            "**/*.svelte",
            "**/*.astro",
            "**/*.mdx",
        ],
    )

    # Get ignore dirs from config
    ignore_dirs = set(
        source_config.get(
            "ignore_dirs",
            [
                "__pycache__",
                "node_modules",
                "venv",
                "env",
                ".git",
                "dist",
                "build",
                "target",
                "out",
                "site",
            ],
        )
    )

    seen_paths = set()
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        try:
            for pattern in patterns:
                # Use glob with the search directory as base
                for match in glob_module.glob(
                    str(search_dir / pattern), recursive=True
                ):
                    file_path = Path(match)
                    if not file_path.is_file():
                        continue

                    # Get relative path from search_dir for key
                    try:
                        rel_path = file_path.relative_to(search_dir)
                    except ValueError:
                        continue

                    rel_str = str(rel_path)

                    # Skip hidden directories in the relative path
                    rel_parts = rel_path.parts
                    if any(p.startswith(".") for p in rel_parts):
                        continue
                    if any(p in ignore_dirs for p in rel_parts):
                        continue

                    # Deduplicate by relative path string
                    if rel_str in seen_paths:
                        continue
                    seen_paths.add(rel_str)

                    try:
                        content = file_path.read_text(encoding="utf-8")
                        source_files[rel_str] = content
                    except OSError, UnicodeDecodeError:
                        pass
        except OSError:
            pass

    return source_files


def main(argv=None):
    if argv is not None and argv and argv[0] == "build":
        argv = argv[1:]
    elif argv is None and (
        Path(sys.argv[0]).name == "fr-docs"
        and len(sys.argv) > 1
        and sys.argv[1] == "build"
    ):
        sys.argv.pop(1)
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Build the documentation site.")
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

    # Collect source files for code references
    search_includes = search_include_config(config)
    if feature_enabled(config, "code_references") or (
        feature_enabled(config, "search")
        and (search_includes["files"] or search_includes["symbols"])
    ):
        print("📂 Collecting source files for code references...")
        source_files = collect_source_files(config)
        config["_source_files"] = source_files
        print(f"   Found {len(source_files)} source files")

    # Copy static assets (minifying JS/CSS when production)
    docs_path = Path(config["_docs_dir"])
    os.makedirs(Path(config["_out_dir"]), exist_ok=True)
    for legacy_name in (
        "file_index.json",
        "git_meta.json",
        "source_files.json",
        "source_highlights.json",
        "symbol_index.json",
    ):
        Path(config["_out_dir"], legacy_name).unlink(missing_ok=True)
    for name in ("favicon.svg", "script.js", "style.css"):
        src = docs_path / name
        dst = Path(config["_out_dir"]) / name

        try:
            if config.get("production", False) and name.endswith((".js", ".css")):
                _minify_static_asset(config, src, dst, name)
            else:
                shutil.copyfile(src, dst)
        except FileNotFoundError:
            print(f"File not found: {os.getcwd()}, {src}->{dst}")
        except OSError as e:
            print(f"OSError: {e}")

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
    search_index = []
    if feature_enabled(config, "search"):
        search_index = build_search_index(slugs, config)
    config["_search_index"] = search_index

    # Compress search index
    search_json = json.dumps(search_index, separators=(",", ":"))
    search_raw = search_json.encode("utf-8")
    cctx = zstandard.ZstdCompressor(level=_best_zstd_level(search_raw, zstd_level(config)))
    compressed = cctx.compress(search_raw)
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
        f"   Search index: {len(search_raw):,} bytes → {len(compressed):,} zstd ({100 * len(compressed) / len(search_raw):.1f}%)"
    )

    # Save source files for code references
    if (
        feature_enabled(config, "code_references")
        or (search_includes["files"] or search_includes["symbols"])
    ) and config.get("_source_files"):
        raw_size, compressed_size = _write_zstd_json(
            config, "source_files.zst", config["_source_files"]
        )
        print(
            f"   Source files: {len(config['_source_files'])} files saved "
            f"({raw_size:,} bytes → {compressed_size:,} zstd)"
        )

        # Generate source highlights with per-file caching
        cache = BuildCache(str(Path(config["_out_dir"]) / ".build_cache.json"))
        highlights_cache_dir = Path(config["_out_dir"]) / ".highlight_cache"
        highlights_cache_dir.mkdir(parents=True, exist_ok=True)
        source_highlights = {}

        for path, content in config["_source_files"].items():
            content_hash = _compute_hash(content)
            cache_key = f"highlight_{path.replace('/', '__').replace(chr(92), '__')}"
            highlight_cache_file = highlights_cache_dir / f"{cache_key}.zst"

            if (
                cache.needs_regeneration(cache_key, content_hash)
                or not highlight_cache_file.exists()
            ):
                # Need to recompute highlights
                highlighted_lines = highlight_source_lines(content, path)
                source_highlights[path] = highlighted_lines

                # Save to per-file cache
                raw = json.dumps(highlighted_lines, separators=(",", ":")).encode(
                    "utf-8"
                )
                compressed = zstandard.ZstdCompressor(
                    level=_best_zstd_level(raw, zstd_level(config))
                ).compress(raw)
                highlight_cache_file.parent.mkdir(parents=True, exist_ok=True)
                highlight_cache_file.write_bytes(compressed)
                cache.update_cache(cache_key, content_hash)
            else:
                # Load from per-file cache
                with open(highlight_cache_file, "rb") as f:
                    compressed = f.read()
                decompressed = zstandard.ZstdDecompressor().decompress(compressed)
                source_highlights[path] = json.loads(decompressed.decode("utf-8"))

        # Write the highlights to zstd
        if source_highlights:
            raw_size, compressed_size = _write_zstd_json(
                config, "source_highlights.zst", source_highlights
            )
            print(
                f"   Source highlights: {len(source_highlights)} files saved "
                f"({raw_size:,} bytes → {compressed_size:,} zstd)"
            )
        else:
            print("   Source highlights: 0 files saved (0 bytes → 0 zstd)")

    if search_includes["files"] and config.get("_source_files"):
        file_index = [
            {"file": path, "name": Path(path).name}
            for path in sorted(config["_source_files"])
        ]
        raw_size, compressed_size = _write_zstd_json(
            config, "file_index.zst", file_index
        )
        print(
            f"   File index: {len(file_index)} files saved "
            f"({raw_size:,} bytes → {compressed_size:,} zstd)"
        )

    # Save symbol index for search
    if search_includes["symbols"] and config.get("_symbol_index"):
        raw_size, compressed_size = _write_zstd_json(
            config, "symbol_index.zst", config["_symbol_index"]
        )
        print(
            f"   Symbol index: {len(config['_symbol_index'])} symbols saved "
            f"({raw_size:,} bytes → {compressed_size:,} zstd)"
        )

    # Git metadata
    git_meta = collect_git_metadata(config)
    raw_size, compressed_size = _write_zstd_json(config, "git_meta.zst", git_meta)
    print(f"   Git metadata: {raw_size:,} bytes → {compressed_size:,} zstd")

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
                executor.submit(
                    build_page, slug, config, config["_slug_page_keys"]
                ): slug
                for slug in slugs_to_build
            }
            for fut in concurrent.futures.as_completed(future_to_slug):
                slug = future_to_slug[fut]
                try:
                    fut.result()
                    print(f"  ✓ {slug_output_name(slug, config)}")
                    built += 1
                except Exception as e:  # noqa: BLE001
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
