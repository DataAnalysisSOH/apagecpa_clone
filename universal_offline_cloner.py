#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import os
import time
import hashlib
import urllib.request
import urllib.parse
from pathlib import Path
from yt_dlp import YoutubeDL

# ---------------- CONFIG ----------------
BASE_URL = "https://agapecpa.com"   # 🔁 CHANGE THIS
OUTPUT_DIR = Path("offline_site")

DELAY = 0.2
TIMEOUT = 15

HEADERS = {"User-Agent": "Mozilla/5.0"}

ASSET_EXT = (
    ".jpg",".jpeg",".png",".gif",".webp",".svg",".ico",".avif",
    ".css",".js",".woff",".woff2",".ttf",".eot",".mp4"
)

YOUTUBE_REGEX = re.compile(
    r'https?://(?:www\.)?(?:youtube\.com/watch\?v=[\w-]+|youtu\.be/[\w-]+)',
    re.I
)

# ----------------------------------------

visited_pages = set()
downloaded_assets = {}

# ---------- UTIL ----------
def safe_path(url):
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.lstrip("/")
    
    if not path or path.endswith("/"):
        path += "index.html"
    
    return OUTPUT_DIR / path


def request(url):
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=TIMEOUT)


def download_file(url):
    if url in downloaded_assets:
        return downloaded_assets[url]

    try:
        resp = request(url)
        data = resp.read()
    except Exception as e:
        print(f"[FAIL] {url}")
        return None

    path = safe_path(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

    downloaded_assets[url] = path
    print(f"[ok] {url}")

    time.sleep(DELAY)
    return path


def resolve(base, link):
    link = link.strip('"\'')
    
    if link.startswith("//"):
        return "https:" + link
    if link.startswith("http"):
        return link
    if link.startswith("/"):
        return urllib.parse.urljoin(base, link)
    
    return urllib.parse.urljoin(base + "/", link)


# ---------- YOUTUBE ----------
def download_youtube(url):
    video_id = url.split("v=")[-1] if "watch?v=" in url else url.split("/")[-1]
    out = OUTPUT_DIR / "videos" / f"{video_id}.mp4"

    if out.exists():
        return out

    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        with YoutubeDL({
            "format": "mp4",
            "outtmpl": str(out),
            "quiet": True
        }) as ydl:
            ydl.download([url])

        print(f"[yt] {url}")
        return out
    except:
        print(f"[YT FAIL] {url}")
        return None


# ---------- PARSER ----------
LINK_RE = re.compile(r'(href|src|data-src)=["\']([^"\']+)["\']', re.I)
CSS_URL_RE = re.compile(r'url\(([^)]+)\)', re.I)


def extract_links(html):
    links = set()

    for _, val in LINK_RE.findall(html):
        links.add(val)

    for val in CSS_URL_RE.findall(html):
        links.add(val)

    return links


# ---------- CORE ----------
def process_page(url):
    if url in visited_pages:
        return
    
    visited_pages.add(url)

    print(f"\n[PAGE] {url}")

    try:
        resp = request(url)
        html = resp.read().decode("utf-8", errors="replace")
    except:
        print(f"[PAGE FAIL] {url}")
        return

    local_path = safe_path(url)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    links = extract_links(html)

    for link in links:
        full = resolve(url, link)

        if not full:
            continue

        # 🎥 YouTube
        if YOUTUBE_REGEX.search(full):
            local_vid = download_youtube(full)
            if local_vid:
                html = html.replace(link, local_vid.relative_to(local_path.parent).as_posix())
            continue

        # 📄 internal page
        if full.startswith(BASE_URL) and not full.lower().endswith(ASSET_EXT):
            process_page(full)
            rel = safe_path(full).relative_to(local_path.parent)
            html = html.replace(link, rel.as_posix())
            continue

        # 📦 asset
        if full.lower().endswith(ASSET_EXT):
            local_asset = download_file(full)
            if local_asset:
                rel = local_asset.relative_to(local_path.parent)
                html = html.replace(link, rel.as_posix())

    local_path.write_text(html, encoding="utf-8")
    print(f"[saved] {local_path}")


# ---------- MAIN ----------
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    print(f"Cloning: {BASE_URL}\n")

    process_page(BASE_URL)

    print("\n✅ DONE — FULL OFFLINE SITE READY")


if __name__ == "__main__":
    main()