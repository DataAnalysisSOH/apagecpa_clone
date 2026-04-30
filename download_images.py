#!/usr/bin/env python3
"""
========================================================
  Agape CPA — Full-Site Image Downloader & Localizer
========================================================
Crawls every page of https://agapecpa.com, downloads
all images into a local `images/` folder, and saves each
page as an HTML file with all image src/srcset attributes
replaced by local relative paths.

Requirements: Python 3.8+  (no third-party libraries needed)

Usage:
    python3 agapecpa_image_downloader.py

Output structure:
    agapecpa_site/
    ├── index.html                        ← https://agapecpa.com/
    ├── about/
    │   └── index.html
    ├── services/
    │   └── index.html
    └── images/
        ├── logo.png
        ├── banner.jpg
        └── ...  (all images, deduplicated, flat folder)
"""

import os
import re
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from collections import deque
from html.parser import HTMLParser

# ── Configuration ──────────────────────────────────────────────────────────────

BASE_URL   = "https://agapecpa.com"
OUTPUT_DIR = Path("agapecpa_site")
IMAGES_DIR = OUTPUT_DIR / "images"

# Only crawl pages that start with this prefix (keeps us on-site)
ALLOWED_PREFIX = "https://agapecpa.com"

# URL path segments to skip
SKIP_PATTERNS = [
    "/checkout", "/cart", "/my-account", "/wp-admin",
    "/wp-login", "/wp-json", "/feed", "/xmlrpc",
    "?add-to-cart", "?wc-ajax", "#",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

CRAWL_DELAY = 0.5   # seconds between requests (be polite)
MAX_PAGES   = 500   # safety cap


# ── HTML Parsing ───────────────────────────────────────────────────────────────

class LinkAndImageParser(HTMLParser):
    """Extract all href links and image src / srcset URLs from an HTML page."""

    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.links  = set()
        self.images = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "a":
            href = attrs.get("href", "")
            if href:
                abs_url = urllib.parse.urljoin(self.base_url, href)
                self.links.add(abs_url)

        if tag in ("img", "source"):
            # src
            src = attrs.get("src", "")
            if src:
                self.images.add(urllib.parse.urljoin(self.base_url, src))
            # srcset  →  "url1 1x, url2 2x"
            srcset = attrs.get("srcset", "")
            for part in srcset.split(","):
                url = part.strip().split()[0] if part.strip() else ""
                if url:
                    self.images.add(urllib.parse.urljoin(self.base_url, url))
            # data-src / data-srcset (lazy-load)
            data_src = attrs.get("data-src", "")
            if data_src:
                self.images.add(urllib.parse.urljoin(self.base_url, data_src))
            data_srcset = attrs.get("data-srcset", "")
            for part in data_srcset.split(","):
                url = part.strip().split()[0] if part.strip() else ""
                if url:
                    self.images.add(urllib.parse.urljoin(self.base_url, url))

        # background images in style attributes
        style = attrs.get("style", "")
        for m in re.finditer(r'url\(["\']?([^"\')\s]+)["\']?\)', style):
            self.images.add(urllib.parse.urljoin(self.base_url, m.group(1)))


# ── Helpers ────────────────────────────────────────────────────────────────────

def fetch(url, binary=False, retries=2):
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read() if binary else r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            print(f"    HTTP {e.code} — {url}")
            return None
        except Exception as e:
            if attempt < retries:
                time.sleep(1)
            else:
                print(f"    ERROR fetching {url}: {e}")
                return None


def url_to_local_page_path(url):
    """
    Convert a page URL to a local file path.
      https://agapecpa.com/         →  agapecpa_site/index.html
      https://agapecpa.com/about/   →  agapecpa_site/about/index.html
    """
    parsed = urllib.parse.urlparse(url)
    path   = parsed.path.strip("/")
    if not path:
        return OUTPUT_DIR / "index.html"
    return OUTPUT_DIR / path / "index.html"


def url_to_local_image_filename(url):
    """
    All images go into a flat images/ folder.
    Strip query strings, keep original filename.
    """
    parsed   = urllib.parse.urlparse(url)
    filename = Path(parsed.path).name
    if not filename or "." not in filename:
        filename = f"img_{abs(hash(url)) % 10**8}.bin"
    return filename


def relative_path_from_page(page_url, image_filename):
    """
    Return the relative path string from a saved page HTML file
    to the images/ directory.
    """
    page_local = url_to_local_page_path(page_url)
    depth = len(page_local.parts) - len(OUTPUT_DIR.parts) - 1
    prefix = "../" * depth if depth > 0 else "./"
    return f"{prefix}images/{image_filename}"


def should_skip(url):
    for pat in SKIP_PATTERNS:
        if pat in url:
            return True
    low = url.lower()
    for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
                ".pdf", ".zip", ".mp4", ".mp3", ".css", ".js"):
        if low.split("?")[0].endswith(ext):
            return True
    return False


def dedupe_filename(filename, used_names):
    """If filename already used for a different URL, append a counter."""
    if filename not in used_names:
        return filename
    stem   = Path(filename).stem
    suffix = Path(filename).suffix
    i = 2
    while True:
        candidate = f"{stem}_{i}{suffix}"
        if candidate not in used_names:
            return candidate
        i += 1


# ── Main Crawler ───────────────────────────────────────────────────────────────

def crawl():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    visited_pages  = set()
    queue          = deque([BASE_URL + "/"])
    image_url_map  = {}   # remote image URL → local filename
    used_filenames = {}   # filename → remote URL (for dedup)

    page_count = 0

    print(f"Starting crawl of {BASE_URL}")
    print(f"Output directory: {OUTPUT_DIR.resolve()}\n")

    while queue and page_count < MAX_PAGES:
        url = queue.popleft()

        url = url.split("#")[0].rstrip("/") + "/"
        if url in visited_pages:
            continue
        if not url.startswith(ALLOWED_PREFIX):
            continue
        if should_skip(url):
            continue

        visited_pages.add(url)
        page_count += 1
        print(f"[{page_count}] Crawling: {url}")

        html = fetch(url)
        if html is None:
            continue

        parser = LinkAndImageParser(url)
        parser.feed(html)

        # Queue new internal links
        for link in parser.links:
            link = link.split("#")[0].rstrip("/") + "/"
            if (link not in visited_pages
                    and link.startswith(ALLOWED_PREFIX)
                    and not should_skip(link)):
                queue.append(link)

        # ── Download images ──────────────────────────────────────────────────
        page_image_map = {}

        for img_url in parser.images:
            if not img_url.startswith("http"):
                continue

            if img_url in image_url_map:
                local_filename = image_url_map[img_url]
            else:
                raw_filename   = url_to_local_image_filename(img_url)
                local_filename = dedupe_filename(raw_filename, used_filenames)
                local_path     = IMAGES_DIR / local_filename

                if not local_path.exists():
                    print(f"     ↳ img  {local_filename}  ←  {img_url}")
                    data = fetch(img_url, binary=True)
                    if data:
                        local_path.write_bytes(data)
                    else:
                        local_filename = None

                if local_filename:
                    image_url_map[img_url]      = local_filename
                    used_filenames[local_filename] = img_url

            if local_filename:
                rel = relative_path_from_page(url, local_filename)
                page_image_map[img_url] = rel

        # ── Rewrite & save HTML ──────────────────────────────────────────────
        modified_html = rewrite_html(html, page_image_map)
        page_path = url_to_local_page_path(url)
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(modified_html, encoding="utf-8")
        print(f"     ✓ saved → {page_path}")

        time.sleep(CRAWL_DELAY)

    # ── Summary ──────────────────────────────────────────────────────────────
    saved_images = len([f for f in IMAGES_DIR.iterdir() if f.is_file()])
    print(f"\n{'='*60}")
    print(f"Crawl complete.")
    print(f"  Pages saved : {page_count}")
    print(f"  Images saved: {saved_images}")
    print(f"  Output dir  : {OUTPUT_DIR.resolve()}")


# ── HTML Rewriter ─────────────────────────────────────────────────────────────

def rewrite_html(html, image_map):
    """
    Replace every remote image URL in the HTML with its local relative path.
    Handles src, srcset, data-src, data-srcset, and CSS url().
    """
    if not image_map:
        return html

    sorted_pairs = sorted(image_map.items(), key=lambda kv: len(kv[0]), reverse=True)

    for remote_url, local_rel in sorted_pairs:
        html = html.replace(remote_url, local_rel)
        no_scheme = remote_url.replace("https://", "//").replace("http://", "//")
        html = html.replace(no_scheme, local_rel)

    return html


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    crawl()