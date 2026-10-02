"""
One-off patch: adds a 'chunk_ready' column to manifest.csv, marking pages
that are reference-only / not real prose content (so Phase 2 skips them
during chunking instead of accidentally treating link-lists as FAQ answers).

Run once, from Capstone_project root:
    python patch_manifest_flags.py
"""

import csv
from pathlib import Path

MANIFEST_PATH = Path("data/manifest.csv")

# filenames whose cleaned content is a document-index / link-list, not prose
EXCLUDE_FROM_CHUNKING = {
    "slabs_wht_forms.html": "Bare link list to further form categories (Withholding Tax Forms, "
                             "Miscellaneous Forms, SOPs/Documents) - no instructional text. Kept as "
                             "a reference pointer only, per deliberate scope decision.",
    "slabs_wht_rates.html": "Page is a table of PDF/xlsx download links for Tax Years 2021-2027, "
                             "not prose. We already extracted the current-year (2027) PDF directly "
                             "as a separate source - this cleaned file is redundant for chunking.",
}


def main():
    if not MANIFEST_PATH.exists():
        print(f"ERROR: {MANIFEST_PATH} not found. Run fetch_sources.py first.")
        return

    with open(MANIFEST_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        raw_filename = Path(row["raw_path"]).name
        if raw_filename in EXCLUDE_FROM_CHUNKING:
            row["chunk_ready"] = "FALSE"
            row["notes"] = EXCLUDE_FROM_CHUNKING[raw_filename]
        else:
            row["chunk_ready"] = "TRUE"
            row["notes"] = ""

    fieldnames = ["topic", "title", "source_url", "raw_path", "cleaned_path", "status", "chunk_ready", "notes"]
    with open(MANIFEST_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    excluded = [r["title"] for r in rows if r["chunk_ready"] == "FALSE"]
    print(f"Manifest updated: {len(rows)} total rows, {len(excluded)} flagged chunk_ready=FALSE:")
    for title in excluded:
        print(f"  - {title}")


if __name__ == "__main__":
    main()