"""
FBR Tax FAQ RAG Chatbot — Phase 2, Step 1: Extraction

Runs Docling ONCE per source (the expensive layout-analysis + TableFormer
step) and caches the result as DoclingDocument JSON. Chunking (step 2) then
reads from these cached files, so tweaking chunk size/logic never requires
re-running Docling on the actual documents.

Usage:
    python 1_extract.py
"""

from pathlib import Path

from docling.document_converter import DocumentConverter

from fbr_common import load_eligible_rows, pick_input_path

DOCLING_JSON_DIR = Path("data/docling_json")


def main():
    eligible = load_eligible_rows()
    print(f"{len(eligible)} sources eligible for extraction\n")

    DOCLING_JSON_DIR.mkdir(parents=True, exist_ok=True)
    converter = DocumentConverter()
    failures = []

    for row in eligible:
        input_path = pick_input_path(row)
        out_path = DOCLING_JSON_DIR / f"{input_path.stem}.json"
        print(f"[{row['topic']}] {row['title']} <- {input_path}")

        if not input_path.exists():
            print(f"  [MISSING] file not found on disk, skipping")
            failures.append((row["title"], "file not found"))
            continue

        if out_path.exists():
            print(f"  [SKIP] already extracted -> {out_path}")
            continue

        try:
            result = converter.convert(str(input_path))
            result.document.save_as_json(out_path)
            print(f"  -> saved {out_path}")
        except Exception as e:
            print(f"  [DOCLING FAILED] {e}")
            failures.append((row["title"], str(e)))

    print(f"\nDone. {len(list(DOCLING_JSON_DIR.glob('*.json')))} documents cached in {DOCLING_JSON_DIR}")
    if failures:
        print(f"\n{len(failures)} sources failed extraction:")
        for title, reason in failures:
            print(f"  - {title}: {reason}")


if __name__ == "__main__":
    main()