"""
FBR Tax FAQ RAG Chatbot — Phase 4, Step 3: Spot-Check Generation

Runs generate_answer() over every question in eval_questions.csv and writes
a Markdown report for manual review, per the roadmap's Phase 4 exit
criteria: "Manual spot-check against eval set for hallucination,
over-answering, or ignoring 'I don't know.'"

This does NOT auto-grade correctness -- that's Phase 6's formal evaluation
against the full eval set (rule 3.1). This is the honest, cheaper first
pass: read every answer next to its expected_behavior and flag anything
off by eye, same spirit as spotcheck.py in Phase 2.

It does run two automated checks that don't need a human eye:
  - "refusal"/"clarification" type questions should have NO cited sources
    (a citation there means the model complied with something it should
    have refused or asked about instead).
  - "direct"/"paraphrase"/"calculation" type questions SHOULD have at
    least one cited source (a citation-free answer there is likely an
    unwarranted refusal or an ungrounded answer).
Both are flagged for review, not auto-failed -- rule 3.2 says report
honestly, not silently "fix" borderline cases.

Usage:
    python spot_check_generation.py
    python spot_check_generation.py --out data/phase4_spotcheck.md
"""

import argparse
import csv
from pathlib import Path

from generate import generate_answer

EVAL_PATH = Path("eval_questions.csv")
DEFAULT_OUT = Path("data/phase4_spotcheck.md")

# question types where a citation appearing is a red flag, not a good sign
NO_CITATION_EXPECTED = {"refusal", "clarification"}
# question types where a MISSING citation is the red flag
CITATION_EXPECTED = {"direct", "paraphrase", "calculation"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if not EVAL_PATH.exists():
        print(f"ERROR: {EVAL_PATH} not found.")
        return

    with open(EVAL_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Running generation on {len(rows)} eval questions...\n")

    flagged = []
    report_lines = ["# Phase 4 Generation Spot-Check\n"]

    for row in rows:
        qid, question, topic, qtype, expected = (
            row["id"], row["question"], row["topic"], row["type"], row["expected_behavior"]
        )
        print(f"[{qid}] ({qtype}) {question}")

        result = generate_answer(question)
        has_citations = bool(result["cited_sources"])

        flag = None
        if qtype in NO_CITATION_EXPECTED and has_citations:
            flag = "UNEXPECTED CITATION — check this wasn't supposed to refuse/clarify"
        elif qtype in CITATION_EXPECTED and not has_citations:
            flag = "NO CITATION — check this wasn't an unwarranted refusal"

        if flag:
            flagged.append((qid, flag))
            print(f"  [FLAG] {flag}")

        report_lines.append(f"## Q{qid} ({topic} / {qtype})\n")
        report_lines.append(f"**Question:** {question}\n")
        report_lines.append(f"**Expected behavior:** {expected}\n")
        report_lines.append(f"**Answer:**\n\n{result['answer']}\n")
        if result["cited_sources"]:
            report_lines.append("**Cited sources:**")
            for s in result["cited_sources"]:
                report_lines.append(f"- {s['marker']} {s['title']} — {s['source_url']}")
        else:
            report_lines.append("**Cited sources:** none")
        report_lines.append(f"\n**Retrieved chunk IDs (all {len(result['retrieved_chunk_ids'])}):** "
                             f"{', '.join(result['retrieved_chunk_ids'])}\n")
        if flag:
            report_lines.append(f"**AUTOMATED FLAG:** {flag}\n")
        report_lines.append("**Manual review:** _(hallucination? over-answering? "
                             "ignored a correct 'I don't know'? — fill in by hand)_\n")
        report_lines.append("---\n")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"\nDone. Report written to {args.out}")
    print(f"{len(flagged)} automated flags out of {len(rows)} questions:")
    for qid, flag in flagged:
        print(f"  Q{qid}: {flag}")
    if not flagged:
        print("  (none)")
    print("\nNow read the report and manually mark each answer for "
          "hallucination / over-answering / wrongly-confident refusal of "
          "a covered question.")


if __name__ == "__main__":
    main()