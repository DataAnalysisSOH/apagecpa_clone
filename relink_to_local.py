#!/usr/bin/env python3
"""
========================================================
  Absolute → Relative Reference Relinker
========================================================
Post-processes a folder of already-downloaded HTML files
(e.g. from agapecpa_image_downloader.py) and rewrites
every absolute URL that points to a local asset
(image, CSS, JS, font, etc.) into a relative path.

Works on:
  • src="https://agapecpa.com/..."
  • href="https://agapecpa.com/..."
  • srcset="https://agapecpa.com/... 1x, ..."
  • data-src / data-srcset (lazy-load)
  • CSS url("https://agapecpa.com/...")
  • Protocol-relative  //agapecpa.com/...

Requirements: Python 3.8+  (stdlib only)

Usage:
    # Default: rewrites agapecpa_site/ in-place
    python3 relink_to_local.py

    # Custom site folder and origin
    python3 relink_to_local.py --dir my_site --origin https://agapecpa.com

    # Dry-run: show what would change without writing
    python3 relink_to_local.py --dry-run

    # Write rewritten copies to a new folder instead of in-place
    python3 relink_to_local.py --out relinked_site
"""

import re
import sys
import shutil
import argparse
import urllib.parse
from pathlib import Path

# ── Defaults ───────────────────────────────────────────────────────────────────

DEFAULT_SITE_DIR = "agapecpa_site"
DEFAULT_ORIGIN   = "https://agapecpa.com"

# Attributes whose values are rewritten
URL_ATTRS = {
    "src", "href", "srcset", "data-src", "data-srcset",
    "data-bg", "data-background", "data-lazy-src",
    "poster",   # <video poster="...">
    "action",   # <form action="...">
}

# ── Core logic ─────────────────────────────────────────────────────────────────

def compute_relative(from_file: Path, to_path: str, site_dir: Path) -> str:
    """
    Given:
      from_file  — the HTML file being rewritten  (absolute Path)
      to_path    — the URL path component, e.g. /images/logo.png
      site_dir   — root of the downloaded site    (absolute Path)

    Returns a relative path string, e.g. "../../images/logo.png"
    Uses os.path.relpath which handles all directory depths correctly,
    including URL-encoded paths like %e6%9e%97...
    """
    import os
    # Decode percent-encoding (e.g. %e6%9e%97 → 林) before building the path
    decoded_path = urllib.parse.unquote(to_path.lstrip("/"))
    target = site_dir / decoded_path
    rel = os.path.relpath(str(target), start=str(from_file.parent))
    return rel.replace("\\", "/")   # Windows safety


def is_local_url(url: str, origin: str, proto_origin: str) -> bool:
    """Return True if the URL belongs to our site (absolute or proto-relative)."""
    return url.startswith(origin) or url.startswith(proto_origin)


def strip_origin(url: str, origin: str, proto_origin: str) -> str:
    """Remove the scheme+host prefix, returning the path (+ query + fragment)."""
    if url.startswith(origin):
        return url[len(origin):]
    if url.startswith(proto_origin):
        return url[len(proto_origin):]
    return url


def rewrite_srcset(value: str, html_file: Path, site_dir: Path,
                   origin: str, proto_origin: str) -> str:
    """
    Rewrite a srcset string like:
      "https://agapecpa.com/img/a.jpg 1x, https://agapecpa.com/img/b.jpg 2x"
    """
    parts = value.split(",")
    new_parts = []
    for part in parts:
        tokens = part.strip().split()
        if not tokens:
            new_parts.append(part)
            continue
        url = tokens[0]
        descriptor = " ".join(tokens[1:])   # e.g. "1x" or "480w"
        if is_local_url(url, origin, proto_origin):
            path = strip_origin(url, origin, proto_origin).split("?")[0].split("#")[0]
            url  = compute_relative(html_file, path, site_dir)
        new_parts.append(f"{url} {descriptor}".strip() if descriptor else url)
    return ", ".join(new_parts)


def rewrite_html(content: str, html_file: Path, site_dir: Path,
                 origin: str, proto_origin: str):
    """
    Rewrite all absolute local references in *content* to relative paths.
    Returns (new_content, change_count).
    """
    changes = 0

    # ── 1. HTML attributes ────────────────────────────────────────────────────
    #
    # Matches:  attr="VALUE"  or  attr='VALUE'
    # We capture attr name so we can handle srcset specially.
    #
    attr_pattern = re.compile(
        r'(?P<attr>' + "|".join(re.escape(a) for a in URL_ATTRS) + r')'
        r'\s*=\s*'
        r'(?P<q>["\'])'
        r'(?P<val>[^"\']*)'
        r'(?P=q)',
        re.IGNORECASE,
    )

    def replace_attr(m):
        nonlocal changes
        attr = m.group("attr").lower()
        q    = m.group("q")
        val  = m.group("val")

        if "srcset" in attr:
            new_val = rewrite_srcset(val, html_file, site_dir, origin, proto_origin)
        else:
            if is_local_url(val, origin, proto_origin):
                path    = strip_origin(val, origin, proto_origin).split("?")[0].split("#")[0]
                new_val = compute_relative(html_file, path, site_dir)
            else:
                return m.group(0)   # not our domain — leave alone

        if new_val != val:
            changes += 1
            return f'{m.group("attr")}={q}{new_val}{q}'
        return m.group(0)

    content = attr_pattern.sub(replace_attr, content)

    # ── 2. CSS url() — covers <style> blocks and inline style= ───────────────
    #
    css_url_pattern = re.compile(
        r'url\(\s*(?P<q>["\']?)(?P<val>[^"\')\s]+)(?P=q)\s*\)',
        re.IGNORECASE,
    )

    def replace_css_url(m):
        nonlocal changes
        q   = m.group("q")
        val = m.group("val")
        if is_local_url(val, origin, proto_origin):
            path    = strip_origin(val, origin, proto_origin).split("?")[0].split("#")[0]
            new_val = compute_relative(html_file, path, site_dir)
            if new_val != val:
                changes += 1
                return f"url({q}{new_val}{q})"
        return m.group(0)

    content = css_url_pattern.sub(replace_css_url, content)

    return content, changes


# ── File walker ────────────────────────────────────────────────────────────────

def process_site(site_dir: Path, origin: str,
                 out_dir, dry_run: bool) -> None:

    origin       = origin.rstrip("/")
    proto_origin = "//" + urllib.parse.urlparse(origin).netloc

    html_files = sorted(f for f in site_dir.rglob("*.html") if f.is_file())

    if not html_files:
        print(f"No HTML files found in: {site_dir.resolve()}")
        sys.exit(1)

    print(f"Origin  : {origin}")
    print(f"Site dir: {site_dir.resolve()}")
    if out_dir:
        print(f"Out dir : {out_dir.resolve()}  (copy mode)")
    elif dry_run:
        print("Mode    : DRY RUN (no files written)")
    else:
        print("Mode    : IN-PLACE rewrite")
    print(f"Files   : {len(html_files)} HTML file(s) found\n")

    total_files   = 0
    total_changes = 0

    for html_file in html_files:
        if not html_file.is_file():
            print(f"  [  skipped  ]  {html_file.relative_to(site_dir)}  (not a file)")
            continue
        content = html_file.read_text(encoding="utf-8", errors="replace")

        new_content, n = rewrite_html(content, html_file, site_dir,
                                      origin, proto_origin)

        rel = html_file.relative_to(site_dir)
        if n:
            print(f"  [{n:>4} change(s)]  {rel}")
            total_changes += n
            total_files   += 1
        else:
            print(f"  [  no changes]  {rel}")

        if dry_run:
            continue

        if out_dir:
            dest = out_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(new_content, encoding="utf-8")
        else:
            if new_content != content:
                html_file.write_text(new_content, encoding="utf-8")

    # If out_dir mode, also copy non-HTML assets so the site still works
    if out_dir and not dry_run:
        for asset in site_dir.rglob("*"):
            if asset.is_file() and asset.suffix.lower() != ".html":
                dest = out_dir / asset.relative_to(site_dir)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(asset, dest)

    print(f"\n{'='*60}")
    print(f"Done.")
    print(f"  HTML files with changes : {total_files}")
    print(f"  Total replacements made : {total_changes}")
    if out_dir and not dry_run:
        print(f"  Rewritten site saved to : {out_dir.resolve()}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Rewrite absolute URLs to relative paths in downloaded HTML files."
    )
    parser.add_argument(
        "--dir", default=DEFAULT_SITE_DIR,
        help=f"Downloaded site root folder (default: {DEFAULT_SITE_DIR})"
    )
    parser.add_argument(
        "--origin", default=DEFAULT_ORIGIN,
        help=f"The original site origin to replace (default: {DEFAULT_ORIGIN})"
    )
    parser.add_argument(
        "--out", default=None,
        help="Write rewritten files to this new folder instead of editing in-place"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would change without writing any files"
    )
    args = parser.parse_args()

    site_dir = Path(args.dir).resolve()
    out_dir  = Path(args.out).resolve() if args.out else None

    if not site_dir.exists():
        print(f"ERROR: Site directory not found: {site_dir}")
        sys.exit(1)

    process_site(site_dir, args.origin, out_dir, args.dry_run)


if __name__ == "__main__":
    main()