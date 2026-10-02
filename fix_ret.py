"""
FBR Tax FAQ RAG Chatbot — Data fix: REIT dividend rows in WHT Rate Card 2027

Same pattern as 3_fix_known_issues.py, applied to a row that slipped through
Phase 2 review. Surfaced by Phase 4 generation testing, not retrieval eval:
retrieval correctly returns the right chunk, but the chunk's own wording is
dense enough that Groq (and a human skimming it) confuses two adjacent
REIT-related rows in the "150 Dividend" table:

  1. "REIT and cases other than clauses (a),(ba),(c),(d)" -- 15% ATL / 30%
     Non-ATL -- the GENERAL rate for dividends paid BY a REIT to its own
     investors. This is what "dividends from a REIT" means in plain English,
     but the clause-reference phrasing doesn't read that way on a skim.
  2. "Dividend received by a REIT scheme from a Special Purpose Vehicle" --
     0% / 0% -- income flowing INTO the REIT from an SPV, the opposite
     direction. This is the row that kept getting cited by mistake.
  3. "Dividend received by others from a Special Purpose Vehicle (REIT
     Regulations, 2015)" -- 35% / 70% -- a third, unrelated case.

This script removes the four garbled chunks spanning the whole "150
Dividend" table (chunk boundaries split rows mid-sentence) and replaces
them with one clean chunk per row, each explicit about direction and intent,
flagged manually_corrected=True per the project's traceability rule (2.3).

Run AFTER 2_chunk.py / 3_fix_known_issues.py, then re-run your embedding
script (e.g. embed_and_store.py) so the LanceDB table picks up the new
chunk text -- editing chunks.jsonl alone does not update retrieval.

Usage:
    python fix_reit_dividends.py
"""

import csv
import json
from pathlib import Path

CHUNKS_PATH = Path("data/chunks.jsonl")
MANIFEST_PATH = Path("data/manifest.csv")
SOURCE_STEM = "slabs_wht_rate_card_2027"

# The whole "150 Dividend" table got split across these four chunk_ids,
# with rows cut mid-sentence at chunk boundaries -- confirmed by manual
# inspection against chunks.jsonl.
REMOVE_CHUNK_IDS = {
    f"{SOURCE_STEM}__9",
    f"{SOURCE_STEM}__10",
    f"{SOURCE_STEM}__11",
    f"{SOURCE_STEM}__12",
}

CORRECTION_NOTE = (
    "The '150 Dividend' table was split across four chunks with rows cut "
    "mid-sentence, and its REIT-related rows use confusing clause-reference "
    "phrasing that caused Groq to confuse 'dividends paid BY a REIT' (the "
    "general 15%/30% rate) with 'dividends received BY a REIT FROM an SPV' "
    "(a narrow 0%/0% case) -- verified against the real PDF during Phase 4 "
    "generation testing. Rebuilt as one clean chunk per row."
)

REPLACEMENT_ROWS = [
    {
        "suffix": "fix150_ipp",
        "text": (
            "Section 150 (Dividend), paid by Independent Power Purchasers "
            "(IPPs): ATL rate 7.50%, Non-ATL rate 15.00%. "
            "Reference: Division-I, Part-III of First Schedule read with "
            "R.1 of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix150_reit_general",
        "text": (
            "Section 150 (Dividend), general rate for dividends paid BY a "
            "Real Estate Investment Trust (REIT) to its own investors -- "
            "i.e. any REIT dividend case not covered by the more specific "
            "IPP, mutual-fund, or Special-Purpose-Vehicle rows in this "
            "table: ATL rate 15.00%, Non-ATL rate 30.00%. "
            "Reference: Division-I, Part-III of First Schedule read with "
            "R.1 of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix150_mutual_proportional",
        "text": (
            "Section 150 (Dividend), mutual funds, contingent upon "
            "proportional income derived from average annual investment in "
            "debt securities and equities respectively: ATL rates 25% and "
            "15%, Non-ATL rates 50% and 30%. "
            "Reference: Division-I, Part-III of First Schedule read with "
            "R.1 of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix150_mutual_debt50",
        "text": (
            "Section 150 (Dividend), mutual funds deriving fifty percent or "
            "more income from profit on debt: ATL rate 25.00%, Non-ATL rate "
            "50.00%. Reference: Division-I, Part-III of First Schedule read "
            "with R.1 of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix150_reit_from_spv",
        "text": (
            "Section 150 (Dividend), dividend RECEIVED BY a REIT scheme "
            "FROM a Special Purpose Vehicle (SPV) -- this is income flowing "
            "INTO the REIT, the opposite direction from a REIT paying "
            "dividends to its own investors: ATL rate 0.00%, Non-ATL rate "
            "0.00%. Reference: Division-I, Part-III of First Schedule read "
            "with R.1 of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix150_others_from_spv",
        "text": (
            "Section 150 (Dividend), dividend received by parties OTHER "
            "than a REIT scheme, from a Special Purpose Vehicle as defined "
            "under the Real Estate Investment Trust Regulations, 2015: ATL "
            "rate 35.00%, Non-ATL rate 70.00%. "
            "Reference: Division-I, Part-III of First Schedule read with "
            "R.1 of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix150_no_tax_payable_co",
        "text": (
            "Section 150 (Dividend), a company where no tax is payable by "
            "such company due to exemption of income, carry-forward of "
            "business losses under Part VIII Chapter III, or claim of tax "
            "credits under Part X Chapter III: ATL rate 25.00%, Non-ATL "
            "rate 50.00%. Reference: Division-I, Part-III of First "
            "Schedule read with R.1 of Tenth Schedule."
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
    print(f"Removed {removed_count} chunks (expected {len(REMOVE_CHUNK_IDS)}): "
          f"{sorted(REMOVE_CHUNK_IDS)}")

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

    print(f"Added {len(new_chunks)} clean replacement chunks")
    print(f"Total chunks: {before_count} -> {len(final)}")
    print("\nNow re-run embed_and_store.py so LanceDB picks up the new text.")


if __name__ == "__main__":
    main()