"""Build the persistent Azure/Chroma index for the RFP proposal corpus.

Run from the repository root:
    python scripts/build_rfp_chroma_index.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.azure_client import embed_texts
from src.rfp_engine import _default_historical_chunks
from src.vector_store import (
    ChromaVectorStore,
    _valid_chunks_from_dicts,
)

PERSIST_DIRECTORY = "data/vector_store"
COLLECTION_NAME = "rfp_chunks"
DEFAULT_BATCH_SIZE = 32


def main() -> None:
    chunks, corpus_source = _default_historical_chunks()
    if not chunks:
        raise SystemExit("No RFP chunks found to index.")

    rfp_chunks = _valid_chunks_from_dicts(chunks)
    batch_size = _batch_size()
    start = time.perf_counter()
    print(f"corpus_source: {corpus_source}", flush=True)
    print(f"corpus_chunk_count: {len(rfp_chunks)}", flush=True)
    print(f"embedding_batch_size: {batch_size}", flush=True)
    print(f"persist_directory: {PERSIST_DIRECTORY}", flush=True)
    print(f"collection_name: {COLLECTION_NAME}", flush=True)

    embeddings = []
    texts = [chunk.text for chunk in rfp_chunks]
    for batch_start in range(0, len(texts), batch_size):
        batch_number = (batch_start // batch_size) + 1
        batch = texts[batch_start:batch_start + batch_size]
        print(
            f"embedding_batch: {batch_number} "
            f"({batch_start + 1}-{batch_start + len(batch)} of {len(texts)})",
            flush=True,
        )
        embeddings.extend(embed_texts(batch))

    store = ChromaVectorStore(
        persist_directory=PERSIST_DIRECTORY,
        collection_name=COLLECTION_NAME,
        reset_collection=True,
    )
    store.add_chunks(rfp_chunks, embeddings)
    indexed_count = store.collection.count()
    elapsed = time.perf_counter() - start

    print(f"indexed_chunk_count: {indexed_count}", flush=True)
    print(f"elapsed_seconds: {elapsed:.2f}", flush=True)

    if indexed_count != len(rfp_chunks):
        raise SystemExit(
            "Index build count mismatch: "
            f"{indexed_count} indexed chunks for {len(rfp_chunks)} corpus chunks."
        )


def _batch_size() -> int:
    try:
        value = int(os.getenv("RFP_CHROMA_BUILD_BATCH_SIZE", ""))
    except ValueError:
        return DEFAULT_BATCH_SIZE
    return value if value > 0 else DEFAULT_BATCH_SIZE


if __name__ == "__main__":
    main()
