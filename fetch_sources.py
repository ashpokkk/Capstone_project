"""
FBR Tax FAQ RAG Chatbot — Phase 1: Data Acquisition (final bulk fetch)

Reads every source from sources.csv, fetches it, saves raw (audit trail),
cleans HTML sources via the MainContentArea selector, and logs everything
to data/manifest.csv.

Usage:
    python fetch_sources.py
"""

import csv
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SOURCES_CSV = Path("sources.csv")
RAW_DIR = Path("data/raw")
CLEANED_DIR = Path("data/cleaned")
MANIFEST_PATH = Path("data/manifest.csv")

BINARY_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".docx"}


def is_binary(filename: str) -> bool:
    return Path(filename).suffix.lower() in BINARY_EXTENSIONS


def fetch_html(url: str, filename: str):
    """Fetch + save raw HTML, then extract+save MainContentArea. Returns (success, cleaned_chars)."""
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [FETCH FAILED] {e}")
        return False, 0

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / filename).write_text(resp.text, encoding="utf-8")

    soup = BeautifulSoup(resp.text, "html.parser")
    main_content = soup.find("div", class_="MainContentArea")

    if not main_content:
        print(f"  [WARN] MainContentArea not found — page structure may differ")
        return True, 0

    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    clean_name = filename.replace(Path(filename).suffix, "_clean.html")
    cleaned_html = str(main_content)
    (CLEANED_DIR / clean_name).write_text(cleaned_html, encoding="utf-8")
    return True, len(cleaned_html)


def fetch_binary(url: str, filename: str):
    """Fetch + save a binary file (PDF/xlsx/docx) as-is. Returns (success, byte_count)."""
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [FETCH FAILED] {e}")
        return False, 0

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / filename).write_bytes(resp.content)
    return True, len(resp.content)


def main():
    if not SOURCES_CSV.exists():
        print(f"ERROR: {SOURCES_CSV} not found. Place it in the project root next to this script.")
        return

    with open(SOURCES_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Loaded {len(rows)} sources from {SOURCES_CSV}\n")

    manifest_rows = []
    ok_count = 0

    for row in rows:
        topic, title, url, filename = row["topic"], row["title"], row["url"], row["filename"]
        print(f"[{topic}] {title}")

        if is_binary(filename):
            success, size = fetch_binary(url, filename)
            cleaned_path = ""
        else:
            success, size = fetch_html(url, filename)
            clean_name = filename.replace(Path(filename).suffix, "_clean.html")
            cleaned_path = str(CLEANED_DIR / clean_name) if size else ""

        status = "OK" if success and size else ("FETCH_FAILED" if not success else "CLEAN_FAILED")
        if status == "OK":
            ok_count += 1
            print(f"  Saved {size} {'bytes' if is_binary(filename) else 'chars (cleaned)'}")

        manifest_rows.append({
            "topic": topic,
            "title": title,
            "source_url": url,
            "raw_path": str(RAW_DIR / filename),
            "cleaned_path": cleaned_path,
            "status": status,
        })

        time.sleep(1)

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "topic", "title", "source_url", "raw_path", "cleaned_path", "status"
        ])
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"\nDone: {ok_count}/{len(rows)} sources fetched successfully.")
    print(f"Manifest written to {MANIFEST_PATH}")

    failures = [r for r in manifest_rows if r["status"] != "OK"]
    if failures:
        print("\nSources needing attention:")
        for r in failures:
            print(f"  [{r['status']}] {r['title']} -> {r['source_url']}")


if __name__ == "__main__":
    main()