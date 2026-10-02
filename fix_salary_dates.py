"""
FBR Tax FAQ RAG Chatbot — Phase 3 Finding: Salary Bracket Retrieval Fix

Phase 3 retrieval eval (eval_output.txt) found that Section 149 salary
tax bracket chunks were LOSING every retrieval race against Section 152
(non-resident payments) chunks -- for salary-income questions. Root
cause: 3_fix_known_issues.py cleaned Section 155/151B/152 because those
tables were garbled, but Section 149 was left alone since its numbers
were correct, just "cosmetically messy" (heavy Docling table-dump text:
"Ancillary Information-A = ...", "Reference for Rates = ..." repeated).
That messiness embeds weakly, so the now-clean-but-wrong Section 152
chunks out-compete it for almost any "tax rate" query.

This is the same category of problem 3_fix_known_issues.py solved,
just discovered one phase later (in retrieval eval, not spot-check).
Same remedy: remove the garbled chunks, replace with clean hand-built
ones, flag manually_corrected=True for full auditability.

Also fixes filing_due_dates_clean__0 (Q5 failure), which opens with
garbled table-dump text ("Person, 1 = Due Dates...") that hurt its
embedding the same way.

Run AFTER exclude_form.py, BEFORE re-running 6_embed_and_store.py.

Usage:
    python 9_fix_salary_and_dates.py
"""

import json
from pathlib import Path

CHUNKS_PATH = Path("data/chunks.jsonl")
SALARY_SOURCE_STEM = "slabs_wht_rate_card_2027"
DUE_DATES_SOURCE_STEM = "filing_due_dates"

# The garbled Section 149 salary + pension chunks, confirmed by manual
# inspection of chunks.jsonl to contain only messy table-dump text for
# these brackets (verified against real WHT Rate Card 2027 PDF values).
REMOVE_SALARY_CHUNK_IDS = {
    f"{SALARY_SOURCE_STEM}__3",
    f"{SALARY_SOURCE_STEM}__4",
    f"{SALARY_SOURCE_STEM}__5",
    f"{SALARY_SOURCE_STEM}__6",
    f"{SALARY_SOURCE_STEM}__7",
    f"{SALARY_SOURCE_STEM}__8",
}
REMOVE_DUE_DATES_CHUNK_IDS = {
    f"{DUE_DATES_SOURCE_STEM}_clean__0",
}

CORRECTION_NOTE = (
    "Docling's table extraction produced numerically correct but heavily "
    "table-dump-formatted text (repeated 'Ancillary Information-A = ...' / "
    "'Reference for Rates = ...' boilerplate), which embedded poorly and "
    "lost retrieval races to unrelated, cleaner chunks (discovered during "
    "Phase 3 retrieval eval — see eval_output.txt Q11/Q23/Q24). This chunk "
    "was manually rebuilt with the same values, in plain sentence form."
)

# --- Section 149: Salary --- verified against the real PDF (chunks 3-8)
SALARY_REPLACEMENT_ROWS = [
    {
        "suffix": "fix149_0",
        "text": (
            "Section 149 (Salary): Where taxable income does not exceed "
            "Rs. 600,000, the tax rate is 0%. "
            "Reference: Division-I, Part-I of First Schedule read with "
            "R.10(a) of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix149_1",
        "text": (
            "Section 149 (Salary): Where taxable income exceeds "
            "Rs. 600,000 but does not exceed Rs. 1,200,000, the tax rate "
            "is 1% of the amount exceeding Rs. 600,000. "
            "Reference: Division-I, Part-I of First Schedule read with "
            "R.10(a) of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix149_2",
        "text": (
            "Section 149 (Salary): Where taxable income exceeds "
            "Rs. 1,200,000 but does not exceed Rs. 2,200,000, the tax "
            "rate is Rs. 6,000 plus 11.00% of the amount exceeding "
            "Rs. 1,200,000. "
            "Reference: Division-I, Part-I of First Schedule read with "
            "R.10(a) of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix149_3",
        "text": (
            "Section 149 (Salary): Where taxable income exceeds "
            "Rs. 2,200,000 but does not exceed Rs. 3,200,000, the tax "
            "rate is Rs. 116,000 plus 20.00% of the amount exceeding "
            "Rs. 2,200,000. "
            "Reference: Division-I, Part-I of First Schedule read with "
            "R.10(a) of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix149_4",
        "text": (
            "Section 149 (Salary): Where taxable income exceeds "
            "Rs. 3,200,000 but does not exceed Rs. 4,100,000, the tax "
            "rate is Rs. 316,000 plus 25.00% of the amount exceeding "
            "Rs. 3,200,000. "
            "Reference: Division-I, Part-I of First Schedule read with "
            "R.10(a) of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix149_5",
        "text": (
            "Section 149 (Salary): Where taxable income exceeds "
            "Rs. 4,100,000 but does not exceed Rs. 5,600,000, the tax "
            "rate is Rs. 541,000 plus 29.00% of the amount exceeding "
            "Rs. 4,100,000. "
            "Reference: Division-I, Part-I of First Schedule read with "
            "R.10(a) of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix149_6",
        "text": (
            "Section 149 (Salary): Where taxable income exceeds "
            "Rs. 5,600,000 but does not exceed Rs. 7,000,000, the tax "
            "rate is Rs. 976,000 plus 32.00% of the amount exceeding "
            "Rs. 5,600,000. "
            "Reference: Division-I, Part-I of First Schedule read with "
            "R.10(a) of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix149_7",
        "text": (
            "Section 149 (Salary): Where taxable income exceeds "
            "Rs. 7,000,000, the tax rate is Rs. 1,424,000 plus 35.00% "
            "of the amount exceeding Rs. 7,000,000. "
            "Reference: Division-I, Part-I of First Schedule read with "
            "R.10(a) of Tenth Schedule."
        ),
    },
    {
        "suffix": "fix149ia_0",
        "text": (
            "Section 149(1A) (Pension): Where the amount of pension "
            "received does not exceed Rs. 10 million, the tax rate is 0%. "
            "Reference: Division-I of Part-I of First Schedule."
        ),
    },
    {
        "suffix": "fix149ia_1",
        "text": (
            "Section 149(1A) (Pension), age below 70 years: Where the "
            "amount of pension received exceeds Rs. 10 million, the tax "
            "rate is 5.00% of the amount exceeding Rs. 10 million plus a "
            "10.00% surcharge. "
            "Reference: Division-I of Part-I of First Schedule and "
            "section 4AB."
        ),
    },
]

# --- Filing FAQs: Due Dates --- verified against the real corpus source
DUE_DATES_REPLACEMENT_ROWS = [
    {
        "suffix": "fix_due_dates_0",
        "text": (
            "Income Tax Due Dates: Individuals and Associations of "
            "Persons (AOP) must file their Income Tax Return on or "
            "before 30th September. Companies must file on or before "
            "31st December. Companies with a special tax year must file "
            "on or before 30th September."
        ),
    },
]


def load_source_metadata(stem: str, rows: list[dict]) -> dict:
    for r in rows:
        if r["chunk_id"].startswith(f"{stem}__") or r["chunk_id"].startswith(f"{stem}_clean__"):
            return r
    raise RuntimeError(f"Could not find any chunk for source stem {stem}")


def main():
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f]

    before_count = len(chunks)
    remove_ids = REMOVE_SALARY_CHUNK_IDS | REMOVE_DUE_DATES_CHUNK_IDS
    removed = [c for c in chunks if c["chunk_id"] in remove_ids]
    kept = [c for c in chunks if c["chunk_id"] not in remove_ids]

    print(f"Removing {len(removed)} garbled chunks "
          f"(expected {len(remove_ids)})")
    if len(removed) != len(remove_ids):
        found_ids = {c["chunk_id"] for c in removed}
        missing = remove_ids - found_ids
        print(f"  WARNING: could not find: {missing}")

    salary_meta = load_source_metadata(SALARY_SOURCE_STEM, chunks)
    due_dates_meta = load_source_metadata(DUE_DATES_SOURCE_STEM, chunks)

    new_chunks = []
    for row in SALARY_REPLACEMENT_ROWS:
        new_chunks.append({
            "chunk_id": f"{SALARY_SOURCE_STEM}__{row['suffix']}",
            "text": row["text"],
            "topic": salary_meta["topic"],
            "title": salary_meta["title"],
            "source_url": salary_meta["source_url"],
            "section": None,
            "headings": None,
            "page_numbers": None,
            "raw_path": salary_meta["raw_path"],
            "manually_corrected": True,
            "correction_note": CORRECTION_NOTE,
        })

    for row in DUE_DATES_REPLACEMENT_ROWS:
        new_chunks.append({
            "chunk_id": f"{DUE_DATES_SOURCE_STEM}__{row['suffix']}",
            "text": row["text"],
            "topic": due_dates_meta["topic"],
            "title": due_dates_meta["title"],
            "source_url": due_dates_meta["source_url"],
            "section": None,
            "headings": None,
            "page_numbers": None,
            "raw_path": due_dates_meta["raw_path"],
            "manually_corrected": True,
            "correction_note": CORRECTION_NOTE,
        })

    final = kept + new_chunks
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        for c in final:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"Added {len(new_chunks)} verified replacement chunks "
          f"({len(SALARY_REPLACEMENT_ROWS)} salary/pension + "
          f"{len(DUE_DATES_REPLACEMENT_ROWS)} due dates)")
    print(f"Total chunks: {before_count} -> {len(final)}")


if __name__ == "__main__":
    main()