"""
FBR Tax FAQ RAG Chatbot — Phase 2 Exit Criteria: Spot-Check

Randomly samples chunks from data/chunks.jsonl for manual review, per the
roadmap's Phase 2 exit criteria: "spot-check 10 random chunks for coherence
and correct source attribution."

Also runs an automated pass first: flags any chunk missing source_url,
topic, or title outright (rule 2.3 — these are non-negotiable), since that
check doesn't need a human eye. The random sample is for judgment calls
(does this chunk actually make sense on its own, does it match its source).

Usage:
    python 4_spot_check.py
    python 4_spot_check.py --n 15        # sample size
    python 4_spot_check.py --seed 42     # reproducible sample
"""

import argparse
import json
import random
from pathlib import Path

CHUNKS_PATH = Path("data/chunks.jsonl")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=10, help="sample size")
    parser.add_argument("--seed", type=int, default=None, help="random seed for reproducibility")
    args = parser.parse_args()

    if not CHUNKS_PATH.exists():
        print(f"ERROR: {CHUNKS_PATH} not found. Run 2_chunk.py (and 3_fix_known_issues.py) first.")
        return

    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f]

    print(f"Loaded {len(chunks)} chunks\n")

    # --- Automated pass: missing required metadata (rule 2.3, non-negotiable) ---
    missing_metadata = [
        c for c in chunks
        if not c.get("source_url") or not c.get("topic") or not c.get("title")
    ]
    print(f"=== Automated check: chunks missing source_url/topic/title ===")
    if missing_metadata:
        print(f"FAIL: {len(missing_metadata)} chunks missing required metadata:")
        for c in missing_metadata:
            print(f"  - {c['chunk_id']}: source_url={c.get('source_url')!r} "
                  f"topic={c.get('topic')!r} title={c.get('title')!r}")
    else:
        print(f"PASS: all {len(chunks)} chunks have source_url, topic, and title.")

    # --- Automated pass: suspiciously short chunks (likely extraction noise) ---
    short_chunks = [c for c in chunks if len(c["text"].strip()) < 30]
    print(f"\n=== Automated check: suspiciously short chunks (<30 chars) ===")
    if short_chunks:
        print(f"{len(short_chunks)} short chunks found (may be legitimate, e.g. single-line "
              f"tables — but worth a look):")
        for c in short_chunks:
            print(f"  - {c['chunk_id']}: {c['text']!r}")
    else:
        print("None found.")

    # --- Manual pass: random sample for human coherence/attribution review ---
    rng = random.Random(args.seed)
    sample = rng.sample(chunks, min(args.n, len(chunks)))

    print(f"\n=== Manual review: {len(sample)} randomly sampled chunks ===")
    print("For each: does the text make sense on its own? Does source_url/topic look right?\n")
    for i, c in enumerate(sample, 1):
        print(f"--- Sample {i}/{len(sample)} ---")
        print(f"chunk_id:    {c['chunk_id']}")
        print(f"topic:       {c['topic']}")
        print(f"title:       {c['title']}")
        print(f"source_url:  {c['source_url']}")
        if c.get("manually_corrected"):
            print(f"NOTE:        manually corrected — {c.get('correction_note', '')}")
        print(f"text:        {c['text'][:500]}")
        print()


if __name__ == "__main__":
    main()