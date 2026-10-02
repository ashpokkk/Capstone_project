"""
Phase 1 helper: fetch a page, save raw+cleaned, and auto-discover any
"Contents" sidebar sub-links on that page (the pattern we found on
NTN Registration, File Income Tax Return, ATL, Pay Income Tax, etc.)

Usage:
    python discover_and_fetch.py

Prints discovered sub-links for review -- does NOT auto-fetch them.
We look at the list first, decide what's in scope, THEN fetch.
"""

from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

RAW_DIR = Path("data/raw")
CLEANED_DIR = Path("data/cleaned")
BASE_URL = "https://www.fbr.gov.pk"


def fetch_and_save(url: str, filename: str) -> tuple[str, "BeautifulSoup | None"]:
    """Fetch, save raw HTML, extract+save MainContentArea. Returns (raw_html, main_content_soup)."""
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / filename).write_text(resp.text, encoding="utf-8")

    soup = BeautifulSoup(resp.text, "html.parser")
    main_content = soup.find("div", class_="MainContentArea")

    if main_content:
        CLEANED_DIR.mkdir(parents=True, exist_ok=True)
        clean_name = filename.replace(".html", "_clean.html")
        (CLEANED_DIR / clean_name).write_text(str(main_content), encoding="utf-8")

    return resp.text, main_content


def discover_subpage_links(main_content) -> list[tuple[str, str]]:
    """
    Find the 'Contents' block inside the main content area and pull out
    every <a href> under it. Fixes the FBR %20/space-before-ID bug.
    Returns list of (title, absolute_url).
    """
    if main_content is None:
        return []

    # Find any tag whose text is exactly "Contents"
    contents_label = main_content.find(
        lambda tag: tag.name in ("p", "strong", "b", "h1", "h2", "h3", "h4", "h5", "h6")
        and tag.get_text(strip=True) == "Contents"
    )

    if contents_label is None:
        return []

    # The link list is usually the next <ul>/<ol> sibling after the label
    link_list = contents_label.find_next(["ul", "ol"])
    if link_list is None:
        return []

    results = []
    for a in link_list.find_all("a", href=True):
        raw_href = a["href"]
        fixed_href = raw_href.replace(" ", "")  # fix the %20/space bug
        absolute_url = urljoin(BASE_URL, fixed_href)
        title = a.get_text(strip=True)
        results.append((title, absolute_url))

    return results


# --------------------------------------------------------------------
# Root pages we already know have nested "Contents" sub-links
# (Type 1 pages, per this conversation's findings)
# --------------------------------------------------------------------
ROOT_PAGES = [
    ("File Income Tax Return",
     "https://www.fbr.gov.pk/categ/file-income-tax-return/51147/80860/71158",
     "filing_file_return.html"),
    ("Active Taxpayer List (ATL)",
     "https://www.fbr.gov.pk/categ/active-taxpayer-list-income-tax/51147/30859/71167",
     "atl_rules.html"),
    ("Pay Income Tax",
     "https://www.fbr.gov.pk/categ/pay-income-tax/51147/40850/81156",
     "pay_income_tax.html"),
]

if __name__ == "__main__":
    for title, url, filename in ROOT_PAGES:
        print(f"\n=== {title} ===")
        _, main_content = fetch_and_save(url, filename)
        subpages = discover_subpage_links(main_content)

        if not subpages:
            print("  No 'Contents' sub-links found (may be a single-page topic, or selector didn't match).")
            continue

        for sub_title, sub_url in subpages:
            print(f"  - {sub_title}: {sub_url}")