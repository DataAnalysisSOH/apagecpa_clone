#!/usr/bin/env python3
"""
Agape CPA — Improved Image Downloader & Localizer
(static HTML version, no browser required)
"""

import re
import time
import hashlib
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from collections import deque
from html.parser import HTMLParser

# ── Config ─────────────────────────────────────────────────────────

BASE_URL = "https://agapecpa.com"
OUTPUT_DIR = Path("agapecpa_site")
IMAGES_DIR = OUTPUT_DIR / "images"

ALLOWED_PREFIX = BASE_URL

CRAWL_DELAY = 0.5
MAX_PAGES = 500

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE_URL,
}

SKIP_PATTERNS = [
    "/checkout", "/cart", "/my-account",
    "/wp-admin", "/wp-login", "/feed"
]

# ── Parser ─────────────────────────────────────────────────────────

class Parser(HTMLParser):
    def __init__(self, base):
        super().__init__()
        self.base = base
        self.links = set()
        self.images = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "a":
            href = attrs.get("href")
            if href:
                self.links.add(urllib.parse.urljoin(self.base, href))

        if tag in ("img", "source"):
            for attr in ["src", "data-src", "data-lazy", "data-original"]:
                val = attrs.get(attr)
                if val:
                    self.images.add(urllib.parse.urljoin(self.base, val))

            for attr in ["srcset", "data-srcset"]:
                val = attrs.get(attr, "")
                for part in val.split(","):
                    u = part.strip().split()[0] if part.strip() else ""
                    if u:
                        self.images.add(urllib.parse.urljoin(self.base, u))

        # inline CSS
        style = attrs.get("style", "")
        for m in re.findall(r'url\(["\']?([^"\')]+)', style):
            self.images.add(urllib.parse.urljoin(self.base, m))

# ── Helpers ────────────────────────────────────────────────────────

def normalize_url(url, page_url):
    if url.startswith("//"):
        url = "https:" + url
    return urllib.parse.urljoin(page_url, url)


def should_skip(url):
    if not url.startswith(ALLOWED_PREFIX):
        return True
    for p in SKIP_PATTERNS:
        if p in url:
            return True
    return False


def fetch(url, binary=False):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read() if binary else r.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"    ✗ {url} ({e})")
        return None


def url_to_path(url):
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return OUTPUT_DIR / "index.html"
    return OUTPUT_DIR / path / "index.html"


def hash_filename(url):
    parsed = urllib.parse.urlparse(url)
    ext = Path(parsed.path).suffix or ".jpg"
    h = hashlib.md5(url.encode()).hexdigest()[:10]
    return f"img_{h}{ext}"


def relative_path(page_url, filename):
    page_path = url_to_path(page_url)
    depth = len(page_path.parts) - len(OUTPUT_DIR.parts) - 1
    prefix = "../" * depth if depth > 0 else "./"
    return f"{prefix}images/{filename}"

# ── HTML Rewrite (FIXED) ───────────────────────────────────────────

def rewrite_html(html, image_map):

    if not image_map:
        return html

    # src / data-src
    def repl_src(m):
        attr, url = m.group(1), m.group(2)
        return f'{attr}="{image_map.get(url, url)}"'

    html = re.sub(r'(src|data-src)=["\']([^"\']+)["\']', repl_src, html, flags=re.I)

    # srcset
    def repl_srcset(m):
        attr, val = m.group(1), m.group(2)
        parts = []
        for item in val.split(","):
            seg = item.strip().split()
            if not seg:
                continue
            u = seg[0]
            rest = " ".join(seg[1:])
            new = image_map.get(u, u)
            parts.append(f"{new} {rest}".strip())
        return f'{attr}="' + ", ".join(parts) + '"'

    html = re.sub(r'(srcset|data-srcset)=["\']([^"\']+)["\']', repl_srcset, html, flags=re.I)

    # CSS url(...)
    def repl_css(m):
        u = m.group(1)
        return f'url("{image_map.get(u, u)}")'

    html = re.sub(r'url\(["\']?([^"\')]+)["\']?\)', repl_css, html, flags=re.I)

    # protocol-less
    for remote, local in image_map.items():
        html = html.replace(remote.replace("https://", "//"), local)

    return html

# ── Main ───────────────────────────────────────────────────────────

def crawl():
    OUTPUT_DIR.mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)

    visited = set()
    queue = deque([BASE_URL + "/"])
    image_map_global = {}

    count = 0

    while queue and count < MAX_PAGES:
        url = queue.popleft().split("#")[0].rstrip("/") + "/"

        if url in visited or should_skip(url):
            continue

        visited.add(url)
        count += 1

        print(f"[{count}] {url}")

        html = fetch(url)
        if not html:
            continue

        parser = Parser(url)
        parser.feed(html)

        for link in parser.links:
            link = link.split("#")[0].rstrip("/") + "/"
            if link not in visited and not should_skip(link):
                queue.append(link)

        page_map = {}

        for img in parser.images:
            img = normalize_url(img, url)

            if not img.startswith("http"):
                continue

            if img in image_map_global:
                filename = image_map_global[img]
            else:
                filename = hash_filename(img)
                path = IMAGES_DIR / filename

                if not path.exists():
                    print(f"     ↳ {filename}")
                    data = fetch(img, binary=True)
                    if data:
                        path.write_bytes(data)
                    else:
                        continue

                image_map_global[img] = filename

            page_map[img] = relative_path(url, filename)

        new_html = rewrite_html(html, page_map)

        out = url_to_path(url)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(new_html, encoding="utf-8")

        print(f"     ✓ saved {out}")

        time.sleep(CRAWL_DELAY)

    print("\nDone.")
    print(f"Pages: {len(visited)}")
    print(f"Images: {len(image_map_global)}")

# ── Entry ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    crawl()