"""
FBR Tax FAQ RAG Chatbot — Phase 2, Step 3: Known-Issue Correction

Docling's table extraction on the WHT Rate Card 2027 PDF broke at two
page-break boundaries (verified by manual comparison against the real PDF,
see project conversation log):

  1. Section 155 (Rent of Immovable Property, Individual/AOP) — the first
     three income brackets had their rate formulas shredded/merged.
  2. Section 151B ("after one year but before completion of four years")
     — this row's data never made it into any table; its text instead
     corrupted the column headers of the following table (Section 152).

This script removes the broken chunks for those regions and replaces them
with clean, verified-correct chunks built directly from the real PDF text.
Every replacement chunk is flagged manually_corrected=True with a note,
per the project's traceability rule (2.3) — nothing here is silent.

Run AFTER 2_chunk.py, before embedding (Phase 3).

Usage:
    python 3_fix_known_issues.py
"""

import csv
import json
from pathlib import Path

CHUNKS_PATH = Path("data/chunks.jsonl")
MANIFEST_PATH = Path("data/manifest.csv")
SOURCE_STEM = "slabs_wht_rate_card_2027"

# Chunk IDs confirmed (by manual inspection) to contain only broken/garbled
# content from the two affected table regions.
REMOVE_CHUNK_IDS = {
    # Section 155 (Rent), Individual/AOP brackets
    f"{SOURCE_STEM}__39",
    f"{SOURCE_STEM}__40",
    # Section 152 table whose headers were corrupted by 151B's missing row
    f"{SOURCE_STEM}__18",
    f"{SOURCE_STEM}__19",
    f"{SOURCE_STEM}__20",
    f"{SOURCE_STEM}__21",
    f"{SOURCE_STEM}__22",
    f"{SOURCE_STEM}__23",
}

CORRECTION_NOTE = (
    "Docling's table extraction produced garbled/incomplete text for this "
    "row (verified against the real PDF during Phase 2 review). This chunk "
    "was manually rebuilt with the correct values."
)

# Verified directly against the real WHT Rate Card 2027 PDF.
REPLACEMENT_ROWS = [
    # --- Section 155: Rent of Immovable Property (Individual and AOP) ---
    {
        "suffix": "fix155_0",
        "text": (
            "Section 155 (Rent of Immovable Property), Individual and AOP: "
            "Where the gross amount of rent does not exceed Rs. 300,000, "
            "the tax rate is Nil. "
            "Reference: Division-V of Part-III of First Schedule read with "
            "R.1 of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix155_1",
        "text": (
            "Section 155 (Rent of Immovable Property), Individual and AOP: "
            "Where the gross amount of rent exceeds Rs. 300,000 but does not "
            "exceed Rs. 600,000, the tax rate is 5.00% of the gross amount "
            "exceeding Rs. 300,000. "
            "Reference: Division-V of Part-III of First Schedule read with "
            "R.1 of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix155_2",
        "text": (
            "Section 155 (Rent of Immovable Property), Individual and AOP: "
            "Where the gross amount of rent exceeds Rs. 600,000 but does not "
            "exceed Rs. 2,000,000, the tax rate is Rs. 15,000 plus 10.00% of "
            "the gross amount exceeding Rs. 600,000. "
            "Reference: Division-V of Part-III of First Schedule read with "
            "R.1 of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix155_3",
        "text": (
            "Section 155 (Rent of Immovable Property), Individual and AOP: "
            "Where the gross amount of rent exceeds Rs. 2,000,000, the tax "
            "rate is Rs. 155,000 plus 25.00% of the gross amount exceeding "
            "Rs. 2,000,000. "
            "Reference: Division-V of Part-III of First Schedule read with "
            "R.1 of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix155_4",
        "text": (
            "Section 155 (Rent of Immovable Property), Company: "
            "ATL Rate 15.00%, Non-ATL Rate 30.00%. "
            "Reference: Division-V of Part-III of First Schedule read with "
            "R.1 of Tenth Schedule."
        ),
    },
    # --- Section 152: Payment to Non-Residents ---
    {
        "suffix": "fix152_1",
        "text": (
            "Section 152 (Payment to Non-Residents), Sub-section (1): "
            "tax rate 15.00%. "
            "Reference: Division-IV of Part-I of First Schedule."
        ),
    },
    {
        "suffix": "fix152_1a",
        "text": (
            "Section 152 (Payment to Non-Residents), Sub-section (1A): "
            "tax rate 7.00%. "
            "Reference: Division-II of Part-III of First Schedule, read "
            "with R.10 (b), (ba), (bb) of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix152_1aa",
        "text": (
            "Section 152 (Payment to Non-Residents), Sub-section (1AA): "
            "tax rate 5.00%. "
            "Reference: Division-II of Part-III of First Schedule, read "
            "with R.10 (b), (ba), (bb) of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix152_1aaa",
        "text": (
            "Section 152 (Payment to Non-Residents), Sub-section (1AAA): "
            "tax rate 10.00%. "
            "Reference: Division-II of Part-III of First Schedule, read "
            "with R.10 (b), (ba), (bb) of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix152_1ba",
        "text": (
            "Section 152 (Payment to Non-Residents), Sub-section (1BA): "
            "tax rate 20.00%. "
            "Reference: Section 152(1BA)."
        ),
    },
    {
        "suffix": "fix152_1c",
        "text": (
            "Section 152 (Payment to Non-Residents), Sub-section (1C): "
            "tax rate 10.00%. "
            "Reference: Division-IV of Part-I of First Schedule."
        ),
    },
    {
        "suffix": "fix152_1d_gt12",
        "text": (
            "Section 152 (Payment to Non-Residents), Sub-section (1D), "
            "Holding period greater than 12 months: tax rate 10.00%. "
            "Reference: Division-II of Part-III of First Schedule."
        ),
    },
    {
        "suffix": "fix152_1d_lt12",
        "text": (
            "Section 152 (Payment to Non-Residents), Sub-section (1D), "
            "Holding period less than 12 months: tax rate 10.00%. "
            "Reference: Division-II of Part-III of First Schedule."
        ),
    },
    {
        "suffix": "fix152_1da",
        "text": (
            "Section 152 (Payment to Non-Residents), Sub-section (1DA), "
            "Capital gain arising on disposal of debt instruments, "
            "Government securities and certificates: tax rate 10.00%. "
            "Reference: Division-II of Part-III of First Schedule."
        ),
    },
    # --- Section 151B: the row that was missing entirely ---
    {
        "suffix": "fix151b_missing_row",
        "text": (
            "Section 151B (Certain payments by life insurance companies and "
            "takaful operators): Where payout or benefit is made after one "
            "year but before completion of four years from the date of "
            "issuance of the life insurance policy, family takaful "
            "certificate or plan — ATL Rate 10.00%; Non-ATL Rate 20.00% "
            "for a Resident Person (Reference: Division IC of Part III of "
            "the First Schedule read with R.1 of Tenth Schedule), or "
            "10.00% for a Non-Resident Person (Reference: Division IC of "
            "Part III of the First Schedule read with R.10(aa) of Tenth "
            "Schedule)."
        ),
    },
]


def load_source_metadata():
    with open(MANIFEST_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if Path(row["raw_path"]).stem == SOURCE_STEM:
                return row
    raise RuntimeError(f"Could not find {SOURCE_STEM} in manifest.csv")


def main():
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f]

    before_count = len(chunks)
    kept = [c for c in chunks if c["chunk_id"] not in REMOVE_CHUNK_IDS]
    removed_count = before_count - len(kept)
    print(f"Removed {removed_count} broken chunks (expected {len(REMOVE_CHUNK_IDS)})")

    src = load_source_metadata()
    new_chunks = []
    for row in REPLACEMENT_ROWS:
        new_chunks.append({
            "chunk_id": f"{SOURCE_STEM}__{row['suffix']}",
            "text": row["text"],
            "topic": src["topic"],
            "title": src["title"],
            "source_url": src["source_url"],
            "section": None,
            "headings": None,
            "page_numbers": None,
            "raw_path": src["raw_path"],
            "manually_corrected": True,
            "correction_note": CORRECTION_NOTE,
        })

    final = kept + new_chunks
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        for c in final:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"Added {len(new_chunks)} verified replacement chunks")
    print(f"Total chunks: {before_count} -> {len(final)}")


if __name__ == "__main__":
    main()