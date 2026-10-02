"""
FBR Tax FAQ RAG Chatbot — Phase 2, Step 5: Exclude Form from Chunking

The manual paper return form (filing_return_form_2024.xlsx) produced 425
raw spreadsheet-cell chunks (74% of the entire corpus) that are not
coherent standalone content -- they're cell labels/values with no
explanatory context (e.g. "Depreciation, Annex-D = 0.25. Depreciation,
Annex-D = ."). Confirmed with the project owner: the actual need was just
a pointer to the form, not its cell contents chunked as FAQ answers.
Step-by-step completion guidance is intentionally out of scope -- the
online Iris filing process (already covered by filing_completing_return_
clean.html) is FBR's actual recommended path.

This script:
  1. Removes all filing_return_form_2024__* chunks from chunks.jsonl
  2. Adds back ONE link-only reference chunk (title + source_url, no
     invented content)
  3. Updates manifest.csv: sets chunk_ready=FALSE for this source and
     logs why, matching the existing pattern from patch_manifest.py

Usage:
    python 5_exclude_form.py
"""

import csv
import json
from pathlib import Path

CHUNKS_PATH = Path("data/chunks.jsonl")
MANIFEST_PATH = Path("data/manifest.csv")
SOURCE_STEM = "filing_return_form_2024"

EXCLUSION_NOTE = (
    "Spreadsheet cell dump does not chunk into coherent standalone content "
    "(425 chunks were raw cell labels/values with no context). Kept as a "
    "link-only reference; step-by-step completion guidance is intentionally "
    "out of scope -- the online Iris filing process is FBR's actual "
    "recommended path and is already covered by a separate source."
)


def main():
    # --- Step 1 & 2: fix chunks.jsonl ---
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f]

    before_count = len(chunks)
    removed = [c for c in chunks if c["chunk_id"].startswith(f"{SOURCE_STEM}__")]
    kept = [c for c in chunks if not c["chunk_id"].startswith(f"{SOURCE_STEM}__")]
    print(f"Removing {len(removed)} raw spreadsheet-cell chunks from {SOURCE_STEM}")

    if not removed:
        print(f"WARNING: no chunks found with prefix '{SOURCE_STEM}__' -- "
              f"check the source was actually chunked, or this script "
              f"already ran.")

    # Pull metadata from one of the removed chunks (or manifest, as fallback)
    if removed:
        meta = removed[0]
    else:
        with open(MANIFEST_PATH, newline="", encoding="utf-8") as f:
            row = next(r for r in csv.DictReader(f)
                       if Path(r["raw_path"]).stem == SOURCE_STEM)
        meta = {"topic": row["topic"], "title": row["title"],
                "source_url": row["source_url"], "raw_path": row["raw_path"]}

    link_only_chunk = {
        "chunk_id": f"{SOURCE_STEM}__link_only",
        "text": (
            f"{meta['title']} -- this is a downloadable form, available at: "
            f"{meta['source_url']}. Step-by-step completion guidance is not "
            f"covered here; for filing an Income Tax Return, see the online "
            f"Iris filing process instead."
        ),
        "topic": meta["topic"],
        "title": meta["title"],
        "source_url": meta["source_url"],
        "section": None,
        "headings": None,
        "page_numbers": None,
        "raw_path": meta["raw_path"],
        "link_only": True,
    }

    final_chunks = kept + [link_only_chunk]
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        for c in final_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"chunks.jsonl: {before_count} -> {len(final_chunks)} "
          f"(removed {len(removed)}, added 1 link-only reference)")

    # --- Step 3: update manifest.csv ---
    with open(MANIFEST_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys())

    updated = False
    for row in rows:
        if Path(row["raw_path"]).stem == SOURCE_STEM:
            row["chunk_ready"] = "FALSE"
            row["notes"] = EXCLUSION_NOTE
            updated = True

    if updated:
        with open(MANIFEST_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"manifest.csv: {SOURCE_STEM} marked chunk_ready=FALSE")
    else:
        print(f"WARNING: {SOURCE_STEM} not found in manifest.csv -- not updated")


if __name__ == "__main__":
    main()