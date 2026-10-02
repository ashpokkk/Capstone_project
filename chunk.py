"""
FBR Tax FAQ RAG Chatbot — Phase 2, Step 2: Chunking

Reads the cached DoclingDocument JSON files (from 1_extract.py), chunks
each with HybridChunker, and patches on source_url/topic/title — which
Docling doesn't know about and which our grounding requirement (rule 2.3)
makes non-negotiable. Writes everything to data/chunks.jsonl for Phase 3.

Tokenizer is tied to sentence-transformers/all-MiniLM-L6-v2 (our chosen
embedding model) so chunk sizes are correct for the model that will
actually embed them, not some default.

Usage:
    python 2_chunk.py
"""

import json
from pathlib import Path

from docling_core.types.doc import DoclingDocument
from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer

from fbr_common import load_eligible_rows, pick_input_path

DOCLING_JSON_DIR = Path("data/docling_json")
CHUNKS_PATH = Path("data/chunks.jsonl")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
MAX_TOKENS = 256  # all-MiniLM-L6-v2's max sequence length


def main():
    eligible = load_eligible_rows()

    tokenizer = HuggingFaceTokenizer.from_pretrained(
        model_name=EMBEDDING_MODEL, max_tokens=MAX_TOKENS
    )
    chunker = HybridChunker(tokenizer=tokenizer)

    all_chunks = []
    failures = []

    for row in eligible:
        input_path = pick_input_path(row)
        json_path = DOCLING_JSON_DIR / f"{input_path.stem}.json"
        print(f"[{row['topic']}] {row['title']} <- {json_path}")

        if not json_path.exists():
            print(f"  [MISSING] not extracted yet — run 1_extract.py first")
            failures.append((row["title"], "docling json missing"))
            continue

        try:
            doc = DoclingDocument.load_from_json(json_path)
            chunks = list(chunker.chunk(doc))
        except Exception as e:
            print(f"  [CHUNKING FAILED] {e}")
            failures.append((row["title"], str(e)))
            continue

        for i, chunk in enumerate(chunks):
            text = chunker.contextualize(chunk)
            headings = getattr(chunk.meta, "headings", None) or []
            page_numbers = sorted({
                prov.page_no
                for item in getattr(chunk.meta, "doc_items", [])
                for prov in getattr(item, "prov", [])
                if getattr(prov, "page_no", None) is not None
            }) or None

            all_chunks.append({
                "chunk_id": f"{input_path.stem}__{i}",
                "text": text,
                "topic": row["topic"],
                "title": row["title"],
                "source_url": row["source_url"],
                "section": headings[-1] if headings else None,
                "headings": headings,
                "page_numbers": page_numbers,
                "raw_path": row["raw_path"],
            })

        print(f"  -> {len(chunks)} chunks")

    CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"\nDone: {len(all_chunks)} chunks written to {CHUNKS_PATH}")
    if failures:
        print(f"\n{len(failures)} sources failed chunking:")
        for title, reason in failures:
            print(f"  - {title}: {reason}")


if __name__ == "__main__":
    main()