"""
Bridge between the API and the Phase 3/4 pipeline.
generate_answer() (generate.py) already calls retrieve() (retrieve.py),
so this file only calls one function and reshapes the result for the API.
"""

from pathlib import Path

from generate import generate_answer

CHUNKS_PATH = Path("data/chunks.jsonl")


def get_corpus_size() -> int:
    if not CHUNKS_PATH.exists():
        return 0
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        return sum(1 for _ in f)


def run_pipeline(question: str) -> dict:
    result = generate_answer(question)

    sources = [
        {
            "marker": s["marker"],
            "chunk_id": s["chunk_id"],
            "title": s["title"] or "Unknown source",
            "source_url": s["source_url"] or "",
        }
        for s in result["cited_sources"]
    ]

    return {
        "answer": result["answer"],
        "sources": sources,
        # generate.py has no "covered" field, so this is a heuristic:
        # no [n] citations in the answer = refusal, clarifying question,
        # or "not covered" reply
        "covered": len(sources) > 0,
    }