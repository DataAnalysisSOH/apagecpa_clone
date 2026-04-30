#!/usr/bin/env python3
"""
Agape CPA — Full-Site Image Downloader (JS-aware)

Uses Playwright to render pages and capture ALL images,
including lazy-loaded and JavaScript-injected ones.
"""

import os
import re
import time
import hashlib
import urllib.parse
from pathlib import Path
from collections import deque

from playwright.sync_api import sync_playwright

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL = "https://agapecpa.com"
OUTPUT_DIR = Path("agapecpa_site")
IMAGES_DIR = OUTPUT_DIR / "images"

ALLOWED_PREFIX = BASE_URL

CRAWL_DELAY = 0.5
MAX_PAGES = 200

SKIP_PATTERNS = [
    "/checkout", "/cart", "/my-account",
    "/wp-admin", "/wp-login", "/feed"
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def should_skip(url):
    if not url.startswith(ALLOWED_PREFIX):
        return True
    for pat in SKIP_PATTERNS:
        if pat in url:
            return True
    return False


def normalize_url(url):
    url = url.split("#")[0]
    return url.rstrip("/") + "/"


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


# ── Core Extraction ───────────────────────────────────────────────────────────

def extract_images(page):
    """Extract all image URLs from DOM + CSS."""
    return page.evaluate("""
        () => {
            const urls = new Set();

            // <img>, <source>
            document.querySelectorAll("img, source").forEach(el => {
                ["src", "srcset", "data-src", "data-srcset"].forEach(attr => {
                    const val = el.getAttribute(attr);
                    if (!val) return;

                    val.split(",").forEach(part => {
                        const u = part.trim().split(" ")[0];
                        if (u) urls.add(u);
                    });
                });
            });

            // CSS backgrounds (computed)
            document.querySelectorAll("*").forEach(el => {
                const style = getComputedStyle(el);
                const bg = style.backgroundImage;
                if (bg && bg !== "none") {
                    const match = bg.match(/url\\(["']?(.*?)["']?\\)/);
                    if (match) urls.add(match[1]);
                }
            });

            return Array.from(urls);
        }
    """)


def extract_links(page):
    return page.evaluate("""
        () => Array.from(document.querySelectorAll("a"))
            .map(a => a.href)
    """)


# ── Download ──────────────────────────────────────────────────────────────────

def download_image(context, url, path):
    try:
        response = context.request.get(url, timeout=30000)
        if response.ok:
            path.write_bytes(response.body())
            return True
        else:
            print(f"     HTTP {response.status} {url}")
    except Exception as e:
        print(f"     ERROR {url} → {e}")
    return False


# ── HTML Rewrite ──────────────────────────────────────────────────────────────

def rewrite_html(html, mapping):
    for remote, local in sorted(mapping.items(), key=lambda x: -len(x[0])):
        html = html.replace(remote, local)
        html = html.replace(remote.replace("https://", "//"), local)
    return html


# ── Main ──────────────────────────────────────────────────────────────────────

def crawl():
    OUTPUT_DIR.mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)

    visited = set()
    queue = deque([BASE_URL + "/"])

    image_map = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        page = context.new_page()

        count = 0

        while queue and count < MAX_PAGES:
            url = normalize_url(queue.popleft())

            if url in visited or should_skip(url):
                continue

            visited.add(url)
            count += 1

            print(f"[{count}] {url}")

            try:
                page.goto(url, timeout=60000)
                page.wait_for_load_state("networkidle")
            except:
                print("     FAILED to load")
                continue

            # scroll to trigger lazy loading
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

            html = page.content()

            # extract links
            for link in extract_links(page):
                link = normalize_url(link)
                if link not in visited and not should_skip(link):
                    queue.append(link)

            # extract images
            raw_images = extract_images(page)

            page_map = {}

            for img in raw_images:
                if not img:
                    continue

                if img.startswith("//"):
                    img = "https:" + img

                img = urllib.parse.urljoin(url, img)

                if not img.startswith("http"):
                    continue

                if img in image_map:
                    filename = image_map[img]
                else:
                    filename = hash_filename(img)
                    path = IMAGES_DIR / filename

                    if not path.exists():
                        print(f"     ↳ {filename}")
                        if not download_image(context, img, path):
                            continue

                    image_map[img] = filename

                page_map[img] = relative_path(url, filename)

            # save HTML
            new_html = rewrite_html(html, page_map)

            out_path = url_to_path(url)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(new_html, encoding="utf-8")

            print(f"     ✓ saved {out_path}")

            time.sleep(CRAWL_DELAY)

        browser.close()

    print("\nDone.")
    print(f"Pages: {len(visited)}")
    print(f"Images: {len(image_map)}")


if __name__ == "__main__":
    crawl()