"""Shared helpers for Phase 2 scripts."""

import csv
from pathlib import Path

MANIFEST_PATH = Path("data/manifest.csv")


def load_eligible_rows():
    """Rows from manifest.csv that are fetched OK and marked chunk_ready."""
    with open(MANIFEST_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if r["status"] == "OK" and r["chunk_ready"] == "TRUE"]


def pick_input_path(row: dict) -> Path:
    """Cleaned HTML if we have it (already boilerplate-free); otherwise raw
    (only the PDF and xlsx rows, which were never cleaned)."""
    cleaned = row.get("cleaned_path", "").strip()
    return Path(cleaned) if cleaned else Path(row["raw_path"])