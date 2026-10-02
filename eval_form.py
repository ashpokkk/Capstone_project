"""
FBR Tax FAQ RAG Chatbot — Phase 6, Step 1: Full Generation Eval

Runs every question in eval_questions.csv through generate_answer() (the
same function the API calls) and writes a review sheet for manual scoring
against expected_behavior.

This does NOT auto-score correct/partial/hallucinated/refused -- that
requires checking real tax figures and prompt-rule compliance by hand
(project rule 3.2: report honestly, no rounding up, no auto-pass).

What it DOES flag automatically, as a first triage pass only:
  - type=refusal/clarification rows that came back WITH citations
    (expected: no citations -- a refusal citing sources is a red flag)
  - type=direct/paraphrase/calculation rows that came back with NO
    citations (expected: cited -- suggests a retrieval or refusal-logic
    problem, not a scoring nuance)

Usage:
    python eval_full.py
"""

import csv
import json
import time
from pathlib import Path

import groq

from generate import generate_answer

EVAL_CSV = Path("eval_questions.csv")
OUTPUT_JSONL = Path("data/eval_full_results.jsonl")
OUTPUT_CSV = Path("data/eval_full_results.csv")

NO_CITATION_EXPECTED_TYPES = {"refusal", "clarification"}
CITATION_EXPECTED_TYPES = {"direct", "paraphrase", "calculation"}


def generate_with_retry(question, tries=5):
    for attempt in range(tries):
        try:
            return generate_answer(question)
        except groq.RateLimitError:
            wait = 20 * (attempt + 1)
            print(f"  429 rate limit, waiting {wait}s...")
            time.sleep(wait)
    raise RuntimeError("Rate limited too many times, aborting")


def flag_row(qtype: str, has_citations: bool) -> str:
    if qtype in NO_CITATION_EXPECTED_TYPES and has_citations:
        return "CHECK: refusal/clarification type but answer has citations"
    if qtype in CITATION_EXPECTED_TYPES and not has_citations:
        return "CHECK: direct/calc type but answer has NO citations"
    return ""


def main():
    if not EVAL_CSV.exists():
        print(f"ERROR: {EVAL_CSV} not found.")
        return

    with open(EVAL_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Running {len(rows)} eval questions through generate_answer()...\n")

    results = []
    flagged = []

    for row in rows:
        qid, question, qtype = row["id"], row["question"], row["type"]
        print(f"[{qid}] ({qtype}) {question}")

        result = generate_with_retry(question)
        has_citations = len(result["cited_sources"]) > 0
        flag = flag_row(qtype, has_citations)
        if flag:
            flagged.append((qid, flag))
            print(f"    >> {flag}")

        results.append({
            "id": qid,
            "question": question,
            "topic": row["topic"],
            "type": qtype,
            "expected_behavior": row["expected_behavior"],
            "answer": result["answer"],
            "cited_sources": result["cited_sources"],
            "retrieved_chunk_ids": result["retrieved_chunk_ids"],
            "auto_flag": flag,
            "score": "",   # fill by hand: correct / partial / hallucinated / refused / wrong
            "notes": "",   # fill by hand
        })
        time.sleep(25)

    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "question", "topic", "type", "expected_behavior",
            "answer", "num_sources", "auto_flag", "score", "notes",
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({
                "id": r["id"],
                "question": r["question"],
                "topic": r["topic"],
                "type": r["type"],
                "expected_behavior": r["expected_behavior"],
                "answer": r["answer"],
                "num_sources": len(r["cited_sources"]),
                "auto_flag": r["auto_flag"],
                "score": "",
                "notes": "",
            })

    print(f"\nDone. {len(results)} results written to:")
    print(f"  {OUTPUT_JSONL}  (full detail, incl. sources + chunk ids)")
    print(f"  {OUTPUT_CSV}    (open in Excel to score by hand)")

    if flagged:
        print(f"\n{len(flagged)} rows auto-flagged for a closer look first:")
        for qid, flag in flagged:
            print(f"  [{qid}] {flag}")
    else:
        print("\nNo automatic flags. Still score every row by hand -- this only "
              "catches structural mismatches, not correctness.")


if __name__ == "__main__":
    main()