"""
FBR Tax FAQ RAG Chatbot — Phase 3, Step 2: Retrieval

Defines retrieve(query, k) — the reusable function Phase 4 will call.
It embeds the query the exact same way the chunks were embedded
(LanceDB does this automatically since the embedding function is
attached to the table schema), then returns the top-k closest chunks.

No LLM involved here. This is pure retrieval, on purpose (project rule
2.1 — retrieval gets validated before generation touches it).

Usage:
    python 7_retrieve.py                # runs a few manual test queries
    python 7_retrieve.py "your question here"
"""

import sys
from pathlib import Path

import lancedb

LANCEDB_PATH = Path("data/lancedb")
TABLE_NAME = "fbr_chunks"

# Connect once, reuse across calls (Phase 4 will import this pattern)
_db = lancedb.connect(str(LANCEDB_PATH))
_table = _db.open_table(TABLE_NAME)


def retrieve(query: str, k: int = 10) -> list[dict]:
    """
    query  -> embedded automatically by LanceDB (same model as storage)
           -> vector search against the stored chunks
           -> returns top-k matches with text + metadata

    k defaults to 10, not 5 -- Section 149's 8 salary bracket chunks
    are worded too similarly for embedding distance to reliably rank
    the exact right bracket into the top 5 (numeric range lookup isn't
    something semantic search is good at). At k=10 all 8 brackets
    consistently cluster together, so the correct one is always
    included even if not ranked first; Groq (Phase 4) does the actual
    range lookup + math from the full set. See eval_output.txt findings
    (Q11/Q23/Q24) and learnings-and-fixes.md.

    Returns a list of dicts: {text, source_url, title, topic, section,
    chunk_id, manually_corrected, score}
    """
    results = _table.search(query).limit(k).to_list()

    formatted = []
    for r in results:
        formatted.append({
            "chunk_id": r["metadata"]["chunk_id"],
            "text": r["text"],
            "topic": r["metadata"]["topic"],
            "title": r["metadata"]["title"],
            "source_url": r["metadata"]["source_url"],
            "section": r["metadata"]["section"],
            "manually_corrected": r["metadata"]["manually_corrected"],
            "score": r.get("_distance"),  # lower = closer match
        })
    return formatted


def print_results(query: str, k: int = 10):
    print(f"\n{'='*70}")
    print(f"QUERY: {query}")
    print(f"{'='*70}")
    results = retrieve(query, k)
    for i, r in enumerate(results, 1):
        print(f"\n--- Result {i} (distance={r['score']:.4f}) ---")
        print(f"topic:   {r['topic']}")
        print(f"title:   {r['title']}")
        print(f"section: {r['section']}")
        print(f"source:  {r['source_url']}")
        if r["manually_corrected"]:
            print(f"NOTE:    manually corrected chunk")
        print(f"text:    {r['text'][:300]}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single query from command line
        print_results(" ".join(sys.argv[1:]))
    else:
        # A few manual sanity-check queries spanning different topics,
        # so we can eyeball whether retrieval "feels" right before
        # running the full 25-question eval set.
        test_queries = [
            "How do I register for an NTN as a company?",
            "What documents do I need to file my income tax return?",
            "What is the tax rate on rent for individuals?",
            "How long does the Active Taxpayer List stay valid?",
            "Can I check my ATL status by SMS?",
        ]
        for q in test_queries:
            print_results(q)  # uses the k=10 default