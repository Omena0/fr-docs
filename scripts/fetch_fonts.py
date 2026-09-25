#!/usr/bin/env python3
"""Download Google Fonts files and emit a local fonts.css.

Usage:
    python scripts/fetch_fonts.py [--css-url URL] [--out-dir DIR] [--css-out PATH]

Reads the Google Fonts CSS for the given family spec, extracts every
font URL, downloads the font files, and writes a local fonts.css whose
@font-face rules point at the downloaded files.

This lets the site serve fonts from its own origin instead of
fonts.gstatic.com, which is both faster (no third-party round-trip)
and more reliable (no 404s when Google changes the URL scheme).
"""

import argparse
import re
import sys
import urllib.request
from pathlib import Path

DEFAULT_CSS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Inter:ital,opsz,wght@0,14..32,400..800"
    "&family=JetBrains+Mono:wght@400..700&display=swap"
)

# Match a single @font-face block. The pattern is written without
# re.VERBOSE so the literal newlines in Google Fonts CSS are matched
# exactly. Google Fonts CSS always uses the same field order and
# indentation, so this is safe.
FONT_FACE_RE = re.compile(
    r"@font-face\s*\{\n"
    r"\s*font-family:\s*['\"](?P<family>[^'\"]+)['\"]\s*;\n"
    r"\s*font-style:\s*(?P<style>\w+)\s*;\n"
    r"\s*font-weight:\s*(?P<weight>\d+)\s*;\n"
    r"\s*font-display:\s*(?P<display>\w+)\s*;\n"
    r"\s*src:\s*url\((?P<src>[^)]+)\)\s*format\(['\"](?P<format>[^'\"]+)['\"]\)\s*;\n"
    r"\}"
)


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "fr-docs/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def download_font(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "fr-docs/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        if len(data) < 1000:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  ! failed to download {url}: {exc}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--css-url",
        default=DEFAULT_CSS_URL,
        help="Google Fonts CSS URL to fetch (default: Inter + JetBrains Mono)",
    )
    parser.add_argument(
        "--out-dir",
        default="docs/fonts",
        help="Directory to write downloaded font files into",
    )
    parser.add_argument(
        "--css-out",
        default="docs/fonts.css",
        help="Path to write the generated fonts.css into",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching Google Fonts CSS from {args.css_url}")
    css = fetch_text(args.css_url)

    faces = FONT_FACE_RE.findall(css)
    if not faces:
        print("ERROR: no @font-face blocks found in CSS", file=sys.stderr)
        return 1

    print(f"Found {len(faces)} font-face rules")

    local_rules = []
    for family, style, weight, display, src_url, fmt in faces:
        # Strip quotes from the URL if present
        src_url = src_url.strip().strip("'\"")
        # Derive a stable local filename from the URL basename
        fname = Path(src_url.split("?")[0]).name
        if not fname:
            continue
        dest = out_dir / fname
        print(f"  {family} {weight} {style} -> {fname}")
        if not download_font(src_url, dest):
            print(f"  ! skipping {family} {weight} {style} (download failed)")
            continue
        local_rules.append(
            f"""@font-face {{
  font-family: '{family}';
  font-style: {style};
  font-weight: {weight};
  font-display: optional;
  src: url('fonts/{fname}') format('{fmt}');
}}"""
        )

    if not local_rules:
        print("ERROR: no fonts were downloaded", file=sys.stderr)
        return 1

    fonts_css = "\n".join(local_rules) + "\n"
    css_out = Path(args.css_out).resolve()
    css_out.parent.mkdir(parents=True, exist_ok=True)
    css_out.write_text(fonts_css, encoding="utf-8")
    print(f"\nWrote {len(local_rules)} font-face rules to {css_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())