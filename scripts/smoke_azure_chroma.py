"""Smoke test Azure embeddings with Chroma retrieval.

Run from repository root:
    python scripts/smoke_azure_chroma.py
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.azure_client import embed_texts
from src.rfp_preprocessor import RFPChunk
from src.vector_store import ChromaVectorStore

PERSIST_DIRECTORY = "data/vector_store_smoke_test"
COLLECTION_NAME = "azure_smoke_rfp_chunks"


def main() -> None:
    os.chdir(PROJECT_ROOT)
    shutil.rmtree(PROJECT_ROOT / PERSIST_DIRECTORY, ignore_errors=True)

    chunks = [
        RFPChunk(
            chunk_id="smoke-cloud-modernization",
            document_id="smoke-rfp-001",
            title="Cloud Migration and Managed Services",
            section="Scope",
            chunk_index=0,
            text=(
                "Cloud migration support for application modernization, "
                "managed services transition, and platform operations."
            ),
            metadata={"sample": True, "topic": "cloud"},
        ),
        RFPChunk(
            chunk_id="smoke-analytics-dashboard",
            document_id="smoke-rfp-002",
            title="Analytics Dashboard Delivery",
            section="Scope",
            chunk_index=0,
            text=(
                "Data analytics dashboard delivery with stakeholder workshops, "
                "KPI visualization, and reporting requirements."
            ),
            metadata={"sample": True, "topic": "analytics"},
        ),
        RFPChunk(
            chunk_id="smoke-cybersecurity-assessment",
            document_id="smoke-rfp-003",
            title="Cybersecurity Assessment",
            section="Scope",
            chunk_index=0,
            text=(
                "Cybersecurity assessment covering identity access controls, "
                "compliance support, risk findings, and remediation planning."
            ),
            metadata={"sample": True, "topic": "cybersecurity"},
        ),
    ]

    chunk_embeddings = embed_texts([chunk.text for chunk in chunks])
    store = ChromaVectorStore(
        persist_directory=PERSIST_DIRECTORY,
        collection_name=COLLECTION_NAME,
    )
    store.add_chunks(chunks, chunk_embeddings)

    query = "Need support for cloud migration and managed services modernization."
    query_embedding = embed_texts([query])[0]
    results = store.query(query_embedding, top_k=2)

    top_ids = results.get("ids", [[]])[0]
    top_distances = results.get("distances", [[]])[0]
    top_documents = results.get("documents", [[]])[0]
    top_document = top_documents[0] if top_documents else ""

    print(f"stored_chunks: {store.collection.count()}")
    print(f"query_result_count: {len(top_ids)}")
    print(f"top_ids: {top_ids}")
    print(f"top_distances: {top_distances}")
    print(f"top_document_preview: {top_document[:160]}")
    print(f"first_result_mentions_cloud: {'cloud' in top_document.lower()}")


if __name__ == "__main__":
    main()
