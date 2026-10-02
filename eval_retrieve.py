"""
FBR Tax FAQ RAG Chatbot — Phase 3, Step 3: Retrieval Evaluation

Runs every question in data/eval_questions.csv through retrieve() and
prints the top-k results for manual judgment (per roadmap Phase 3 exit
criteria: >=80% of eval questions correctly retrieve the right chunk(s)).

This does NOT auto-grade "correct" vs "incorrect" -- there's no labeled
"right chunk_id" column in the eval set, so a human has to look at each
question's results and judge whether the retrieved text actually
contains the answer. That human judgment is Ayesha's job; this script's
job is just to make that judgment easy and fast.

For refusal/ambiguous questions (types: refusal, clarification), "good"
retrieval looks different -- we're checking that top matches are WEAK
or clearly off-topic, not that something wrong got retrieved
confidently. Actually refusing is a Phase 4 concern (the LLM prompt
layer); retrieval's only job here is not to hand back a confident,
on-topic-looking chunk for something that shouldn't be answered at all.

Usage:
    python 8_eval_retrieval.py
    python 8_eval_retrieval.py --k 3        # change top-k (default 5)
"""

import argparse
import csv
from pathlib import Path

from retrieve import retrieve  # reuses 7_retrieve.py's function

EVAL_PATH = Path("data/eval_questions.csv")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=10, help="top-k results per question")
    args = parser.parse_args()

    if not EVAL_PATH.exists():
        print(f"ERROR: {EVAL_PATH} not found.")
        return

    with open(EVAL_PATH, encoding="utf-8") as f:
        questions = list(csv.DictReader(f))

    print(f"Running {len(questions)} eval questions through retrieval "
          f"(top-{args.k} each)\n")

    for row in questions:
        qid, question, topic, qtype, expected = (
            row["id"], row["question"], row["topic"],
            row["type"], row["expected_behavior"],
        )

        print(f"{'='*80}")
        print(f"Q{qid} [{topic} / {qtype}]: {question}")
        print(f"Expected: {expected}")
        print(f"{'-'*80}")

        results = retrieve(question, k=args.k)
        for i, r in enumerate(results, 1):
            flag = " [MANUALLY CORRECTED]" if r["manually_corrected"] else ""
            print(f"  {i}. (dist={r['score']:.4f}) {r['title']} "
                  f"> {r['section']}{flag}")
            print(f"     {r['text'][:150]}...")

        print()  # spacing between questions


if __name__ == "__main__":
    main()