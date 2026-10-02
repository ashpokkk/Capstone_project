"""
FBR Tax FAQ RAG Chatbot — Phase 3, Step 1: Embed & Store

Reads the 147 chunks from data/chunks.jsonl (Phase 2's output), embeds
each chunk's text using sentence-transformers/all-MiniLM-L6-v2 (free,
local, no API key), and stores everything in a LanceDB table on disk.

We do NOT re-chunk or re-extract here — that already happened in Phase 2.
This script's only job is: text -> vector -> stored, searchable table.

Usage:
    python 6_embed_and_store.py
"""

import json
from pathlib import Path
from typing import List, Optional

import lancedb
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector

CHUNKS_PATH = Path("data/chunks.jsonl")
LANCEDB_PATH = Path("data/lancedb")
TABLE_NAME = "fbr_chunks"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


# --------------------------------------------------------------
# Embedding function: LanceDB will call this automatically
# whenever we call table.add() — we never call the model by hand.
# --------------------------------------------------------------
embedding_func = get_registry().get("sentence-transformers").create(
    name=EMBEDDING_MODEL
)


# --------------------------------------------------------------
# Schema
#
# `text` is the only field that gets embedded into a vector.
# Everything else in `metadata` just rides along with a search
# result, for citation and debugging — it does NOT affect what
# the model considers "similar."
#
# Dropped fields (deliberate, see project notes):
#   - raw_path: local file path, meaningless once deployed
#   - correction_note: identical boilerplate on every corrected
#     chunk, carries no unique info — audit trail lives in
#     Postgres later if ever needed, not here
# --------------------------------------------------------------
class ChunkMetadata(LanceModel):
    # alphabetical order required by pydantic here
    chunk_id: str
    headings: Optional[List[str]] = None
    manually_corrected: Optional[bool] = False
    page_numbers: Optional[List[int]] = None
    section: Optional[str] = None
    source_url: str
    title: str
    topic: str


class Chunks(LanceModel):
    text: str = embedding_func.SourceField()
    vector: Vector(embedding_func.ndims()) = embedding_func.VectorField()  # type: ignore
    metadata: ChunkMetadata


def load_chunks() -> list[dict]:
    """Read chunks.jsonl and reshape each line into our schema's format."""
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(
            f"{CHUNKS_PATH} not found. Run Phase 2 scripts first."
        )

    with open(CHUNKS_PATH, encoding="utf-8") as f:
        raw_chunks = [json.loads(line) for line in f]

    processed = []
    for c in raw_chunks:
        processed.append({
            "text": c["text"],
            "metadata": {
                "chunk_id": c["chunk_id"],
                "headings": c.get("headings"),
                "manually_corrected": c.get("manually_corrected", False),
                "page_numbers": c.get("page_numbers"),
                "section": c.get("section"),
                "source_url": c["source_url"],
                "title": c["title"],
                "topic": c["topic"],
            },
        })
    return processed


def main():
    print(f"Loading chunks from {CHUNKS_PATH}...")
    processed_chunks = load_chunks()
    print(f"Loaded {len(processed_chunks)} chunks")

    print(f"\nConnecting to LanceDB at {LANCEDB_PATH}...")
    db = lancedb.connect(str(LANCEDB_PATH))

    print(f"Creating table '{TABLE_NAME}' (mode=overwrite)...")
    table = db.create_table(TABLE_NAME, schema=Chunks, mode="overwrite")

    print(f"\nEmbedding + adding {len(processed_chunks)} chunks "
          f"(this calls {EMBEDDING_MODEL} on each chunk's text)...")
    table.add(processed_chunks)

    # --- Sanity check (Phase 3 checklist step 5) ---
    row_count = table.count_rows()
    print(f"\nDone. Table has {row_count} rows "
          f"(expected {len(processed_chunks)}).")

    if row_count != len(processed_chunks):
        print("[WARNING] Row count mismatch — something was dropped or "
              "duplicated during add().")

    print("\nSample row:")
    sample = table.to_pandas().iloc[0]
    print(f"  text (first 100 chars): {sample['text'][:100]}...")
    print(f"  metadata: {sample['metadata']}")
    print(f"  vector length: {len(sample['vector'])}")


if __name__ == "__main__":
    main()