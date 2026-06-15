"""Vector retrieval utilities for the RFP assignment workflow.

This file keeps embedding generation separate from retrieval. In local tests we
can pass a small fake embedding function; in production the same interface can
wrap Azure OpenAI embeddings before writing to Chroma.

Run project files from the repository root so imports resolve consistently.
For example: `python src/vector_store.py`.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Any

try:
    from src.rfp_preprocessor import RFPChunk
except ModuleNotFoundError:
    # Allows `python vector_store.py` while working directly inside the src folder.
    from rfp_preprocessor import RFPChunk


EmbeddingFunction = Callable[[Sequence[str]], list[list[float]]]
_DEFAULT_STORE: "InMemoryVectorStore | None" = None
_LAST_CHROMA_TIMINGS: dict[str, Any] = {}
_LAST_CHROMA_QUERY_TIMINGS: dict[str, Any] = {}
_LOCAL_EMBEDDING_TERMS = [
    "cloud",
    "azure",
    "data",
    "analytics",
    "dashboard",
    "security",
    "migration",
    "application",
    "managed",
    "service",
    "delivery",
    "support",
]
_EMBEDDING_BATCH_SIZE = 32

logging.getLogger("chromadb.telemetry.product.posthog").disabled = True


@dataclass(frozen=True)
class SearchResult:
    """A retrieved RFP chunk and its similarity score.

    @param chunk: Retrieved RFP chunk.
    @param score: Similarity score between the query and chunk embedding.
    """

    chunk: RFPChunk
    score: float

    def to_dict(self) -> dict[str, Any]:
        """Convert the search result to a dictionary for API/dashboard output.

        @return: Dictionary containing the score, chunk text, and chunk metadata.
        """

        return {
            "chunk_id": self.chunk.chunk_id,
            "document_id": self.chunk.document_id,
            "title": self.chunk.title,
            "section": self.chunk.section,
            "score": self.score,
            "text": self.chunk.text,
            "metadata": self.chunk.metadata,
        }

    def to_retrieved_example(self) -> dict[str, Any]:
        """Convert the result to the Week 2 dashboard retrieval shape.

        @return: Flat retrieved-example dictionary for assignment context.
        """

        example = {
            "proposal_id": self.chunk.metadata.get(
                "proposal_id",
                self.chunk.document_id,
            ),
            "chunk_id": self.chunk.chunk_id,
            "similarity_score": round(self.score, 4),
            "supporting_text": self.chunk.text,
        }
        _copy_linkage_metadata(example, self.chunk.metadata)
        return example


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Compute cosine similarity between two embedding vectors.

    The vector store uses this score to rank historical RFP chunks against a new
    RFP query. A higher score means the vectors point in a more similar
    direction.

    @param left: First embedding vector.
    @param right: Second embedding vector.
    @return: Cosine similarity score.
    @raises ValueError: If the vectors are empty or have different lengths.
    """

    if len(left) != len(right):
        raise ValueError("Embedding vectors must have the same length")
    if not left:
        raise ValueError("Embedding vectors cannot be empty")

    left_values = [float(value) for value in left]
    right_values = [float(value) for value in right]

    dot_product = sum(a * b for a, b in zip(left_values, right_values))
    left_norm = sqrt(sum(a * a for a in left_values))
    right_norm = sqrt(sum(b * b for b in right_values))

    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot_product / (left_norm * right_norm)


class InMemoryVectorStore:
    """Small vector store for Sprint 1 development without sensitive data.

    @param embedding_function: Function that converts text into embeddings.
    """

    def __init__(self, embedding_function: EmbeddingFunction) -> None:
        """Initialize an empty local vector store.

        @param embedding_function: Function used to embed chunks and queries.
        """

        self.embedding_function = embedding_function
        self._chunks: list[RFPChunk] = []
        self._embeddings: list[list[float]] = []
        self._embedding_dim: int | None = None

    def __len__(self) -> int:
        """Return the number of chunks currently stored.

        @return: Number of stored chunks.
        """

        return len(self._chunks)

    def add_chunks(self, chunks: Sequence[RFPChunk]) -> None:
        """Embed and add chunks to the local store.

        @param chunks: RFP chunks to embed and store.
        @raises ValueError: If the embedding function returns invalid vectors.
        """

        if not chunks:
            return

        # The embedding function is injected so tests can use fake embeddings.
        embeddings = self.embedding_function([chunk.text for chunk in chunks])
        self._validate_embeddings(embeddings, expected_count=len(chunks))

        self._chunks.extend(chunks)
        self._embeddings.extend([list(embedding) for embedding in embeddings])

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """Return the most similar chunks for a new RFP query.

        @param query_text: New RFP text or user query to search with.
        @param top_k: Maximum number of retrieved chunks to return.
        @param min_score: Optional lower bound for similarity scores.
        @return: Ranked search results, highest score first.
        @raises ValueError: If `top_k` is not positive or embeddings are invalid.
        """

        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if not query_text.strip() or not self._chunks:
            return []

        query_embedding = self.embedding_function([query_text])[0]
        self._validate_query_embedding(query_embedding)

        results = [
            SearchResult(
                chunk=chunk,
                score=cosine_similarity(query_embedding, embedding),
            )
            for chunk, embedding in zip(self._chunks, self._embeddings)
        ]

        if min_score is not None:
            results = [result for result in results if result.score >= min_score]

        # Stable sorting makes tests and dashboard examples easier to compare.
        return sorted(
            results,
            key=lambda result: (result.score, result.chunk.chunk_id),
            reverse=True,
        )[:top_k]

    def _validate_embeddings(
        self,
        embeddings: Sequence[Sequence[float]],
        expected_count: int,
    ) -> None:
        """Validate embeddings before adding them to the store.

        @param embeddings: Embeddings returned by the embedding function.
        @param expected_count: Number of chunks that should have embeddings.
        @raises ValueError: If counts or vector dimensions do not match.
        """

        if len(embeddings) != expected_count:
            raise ValueError("Embedding function returned the wrong number of vectors")

        for embedding in embeddings:
            if not embedding:
                raise ValueError("Embedding vectors cannot be empty")
            if self._embedding_dim is None:
                self._embedding_dim = len(embedding)
            elif len(embedding) != self._embedding_dim:
                raise ValueError("All embedding vectors must have the same length")

    def _validate_query_embedding(self, embedding: Sequence[float]) -> None:
        """Validate that a query embedding matches the stored vector size.

        @param embedding: Query embedding vector.
        @raises ValueError: If the query vector dimension does not match.
        """

        if self._embedding_dim is None:
            return
        if len(embedding) != self._embedding_dim:
            raise ValueError("Query embedding has a different length than the store")


class ChromaVectorStore:
    """Thin Chroma wrapper for the real Azure-embedding pipeline.

    @param persist_directory: Local directory for Chroma vector-store files.
    @param collection_name: Chroma collection name for RFP chunks.
    """

    def __init__(
        self,
        persist_directory: str = "data/vector_store",
        collection_name: str = "rfp_chunks",
        reset_collection: bool = False,
        create_if_missing: bool = True,
    ) -> None:
        """Connect to a persistent Chroma collection.

        @param persist_directory: Local directory for Chroma vector-store files.
        @param collection_name: Chroma collection name for RFP chunks.
        @param reset_collection: When true, rebuild the collection from scratch.
        @param create_if_missing: When false, require a reusable collection to
            already exist instead of silently creating an empty one.
        @raises ImportError: If `chromadb` is not installed.
        """

        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError as exc:
            raise ImportError(
                "chromadb is optional and required only for Azure/Chroma "
                "retrieval. Install chromadb to run Chroma smoke tests; "
                "the Streamlit app can use local fallback without it."
            ) from exc

        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )
        if reset_collection:
            try:
                self.client.delete_collection(name=collection_name)
            except Exception:
                # Chroma raises when the collection does not exist; that is fine
                # because get_or_create_collection below will create a fresh one.
                pass
        if reset_collection or create_if_missing:
            self.collection = self.client.get_or_create_collection(name=collection_name)
        else:
            try:
                self.collection = self.client.get_collection(name=collection_name)
            except Exception as exc:
                raise ValueError(
                    f"Reusable Chroma collection not found: {collection_name}"
                ) from exc

    def add_chunks(
        self,
        chunks: Sequence[RFPChunk],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        """Add embedded chunks to the persistent Chroma collection.

        @param chunks: RFP chunks to store.
        @param embeddings: Precomputed embeddings for those chunks.
        @raises ValueError: If the chunk and embedding counts do not match.
        """

        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        if not chunks:
            return

        self.collection.add(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=[list(embedding) for embedding in embeddings],
            metadatas=[_chroma_metadata(chunk) for chunk in chunks],
        )

    def query(
        self,
        query_embedding: Sequence[float],
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Query Chroma using a precomputed embedding vector.

        @param query_embedding: Embedding for the new RFP or query text.
        @param top_k: Maximum number of results to return.
        @return: Raw Chroma query response.
        @raises ValueError: If the query settings are invalid.
        """

        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if not query_embedding:
            raise ValueError("query_embedding cannot be empty")

        return self.collection.query(
            query_embeddings=[list(query_embedding)],
            n_results=top_k,
        )


def build_retrieval_context(
    results: Sequence[SearchResult],
    max_chars: int = 6_000,
) -> str:
    """Format retrieved chunks for a downstream RAG prompt or explanation.

    This gives the later explanation step a compact evidence block with source
    labels and scores. It can also be used directly in debugging output.

    @param results: Ranked retrieval results.
    @param max_chars: Character budget for the formatted context.
    @return: Plain-text context block with numbered retrieved chunks.
    @raises ValueError: If `max_chars` is not positive.
    """

    if max_chars <= 0:
        raise ValueError("max_chars must be positive")

    blocks: list[str] = []
    used_chars = 0

    for result_number, result in enumerate(results, start=1):
        block = (
            f"[{result_number}] {result.chunk.title} | {result.chunk.section} | "
            f"score={result.score:.3f}\n{result.chunk.text}"
        )
        if used_chars + len(block) > max_chars:
            break
        blocks.append(block)
        used_chars += len(block)

    return "\n\n".join(blocks)


def build_dashboard_payload(
    query_text: str,
    results: Sequence[SearchResult],
    rfp_summary: str = "",
    recommended_directors: Sequence[dict[str, Any]] | None = None,
    effort: dict[str, Any] | None = None,
    risk_flags: Sequence[dict[str, str]] | None = None,
    notes: str = "Prototype output for dashboard integration.",
) -> dict[str, Any]:
    """Create the Week 2 dashboard output shape for RFP assignment.

    @param query_text: New RFP text or short query used for retrieval.
    @param results: Retrieved chunks that support the recommendation.
    @param rfp_summary: Optional summary of the new RFP.
    @param recommended_directors: Optional director ranking records.
    @param risk_flags: Optional warning messages for the dashboard.
    @param notes: Optional note about assumptions or missing data.
    @return: Dictionary shaped like the future dashboard/API response.
    """

    supporting_chunks = [result.chunk.chunk_id for result in results]
    directors = [
        _dashboard_director_record(director, supporting_chunks)
        for director in recommended_directors or []
    ]

    return {
        "rfp_summary": rfp_summary or _summarize_query(query_text),
        "effort": effort or {
            "level": "Low",
            "estimated_duration": "1-2 weeks",
            "reason": "Prototype estimate pending final RFP effort model.",
            "rationale": "Prototype estimate pending final RFP effort model.",
        },
        "similar_rfps": [
            {
                "title": result.chunk.title,
                "similarity_score": round(result.score, 4),
                "matched_chunk": result.chunk.text,
                "source": result.chunk.chunk_id,
            }
            for result in results
        ],
        "retrieved_examples": [
            result.to_retrieved_example() for result in results
        ],
        "recommended_directors": directors,
        "risk_flags": list(risk_flags or []),
        "notes": notes,
    }


def build_vector_store(chunks: list[dict]):
    """Build the local vector store expected by the dashboard placeholder.

    @param chunks: Chunk dictionaries from `prepare_rfp_chunks`.
    @return: In-memory vector store populated with those chunks.
    """

    global _DEFAULT_STORE

    store = InMemoryVectorStore(_local_embedding)
    store.add_chunks(_valid_chunks_from_dicts(chunks or []))
    _DEFAULT_STORE = store
    return store


def retrieve_relevant_chunks(query: str, top_k: int = 5):
    """Retrieve chunks from the most recently built local vector store.

    @param query: RFP text or query text to search with.
    @param top_k: Maximum number of chunks to return.
    @return: Ranked retrieved examples with similarity scores.
    """

    if _DEFAULT_STORE is None:
        return []
    return [
        result.to_retrieved_example()
        for result in _DEFAULT_STORE.query(query, top_k=top_k)
    ]


def _chroma_metadata(chunk: RFPChunk) -> dict[str, str | int | float | bool]:
    """Convert chunk metadata into Chroma-safe scalar values.

    Chroma metadata fields need to be simple scalar values. If a metadata value
    is more complex, it is serialized as JSON so the source details are not
    lost.

    @param chunk: RFP chunk being written to Chroma.
    @return: Metadata dictionary accepted by Chroma.
    """

    metadata: dict[str, str | int | float | bool] = {
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "title": chunk.title,
        "section": chunk.section,
        "chunk_index": chunk.chunk_index,
    }

    for key, value in chunk.metadata.items():
        if isinstance(value, str | int | float | bool):
            metadata[key] = value
        elif value is not None:
            # Keep complex metadata instead of dropping it silently.
            metadata[key] = json.dumps(value, sort_keys=True)

    return metadata


def _valid_chunks_from_dicts(chunks: Sequence[dict[str, Any]]) -> list[RFPChunk]:
    """Convert chunk dictionaries and drop entries with no indexable text."""

    return [
        rfp_chunk
        for chunk in chunks
        if (rfp_chunk := _chunk_from_dict(chunk)).text.strip()
    ]


def _chunk_from_dict(chunk: dict[str, Any]) -> RFPChunk:
    """Convert a dashboard chunk dictionary back into an RFPChunk object."""

    proposal_id = str(chunk.get("proposal_id") or "unknown_proposal")
    chunk_index = _as_int(chunk.get("chunk_index"), default=0)
    chunk_id = str(chunk.get("chunk_id") or f"{proposal_id}_chunk_{chunk_index:03d}")
    text = str(chunk.get("text") or "")

    # Normalize multiple supported chunk shapes into a single RFPChunk contract.
    # - Shape A: full `RFPChunk.to_dict()` (document_id + title + section + metadata).
    # - Shape B: Week 3 flat metadata contract (document_id present, title/section optional).
    # - Shape C: Week 2 dashboard chunk contract (no document_id; uses proposal_id/source_type).
    if "document_id" in chunk:
        document_id = str(chunk["document_id"])
        title = chunk.get("title")
        if title is None:
            title = proposal_id if proposal_id != "unknown_proposal" else document_id
        section = chunk.get("section")
        if section is None:
            section = chunk.get("source_type", "proposal")

        metadata = dict(chunk.get("metadata", {}))
        metadata.update(
            {
                "chunk_id": chunk_id,
                "chunk_index": chunk_index,
                "proposal_id": chunk.get("proposal_id", document_id),
                "source_type": chunk.get("source_type", section),
            }
        )
        _copy_linkage_metadata(metadata, chunk)

        return RFPChunk(
            chunk_id=chunk_id,
            document_id=document_id,
            title=str(title),
            section=str(section),
            chunk_index=chunk_index,
            text=text,
            metadata=metadata,
        )

    source_type = str(chunk.get("source_type", "proposal"))
    rfp_chunk = RFPChunk(
        chunk_id=chunk_id,
        document_id=proposal_id,
        title=proposal_id,
        section=source_type,
        chunk_index=chunk_index,
        text=text,
        metadata={
            "proposal_id": proposal_id,
            "chunk_id": chunk_id,
            "source_type": source_type,
            "chunk_index": chunk_index,
        },
    )
    _copy_linkage_metadata(rfp_chunk.metadata, chunk)
    return rfp_chunk


def _local_embedding(texts: Sequence[str]) -> list[list[float]]:
    """Create small deterministic embeddings for local dashboard testing."""

    embeddings: list[list[float]] = []
    for text in texts:
        lower_text = text.lower()
        vector = [float(term in lower_text) for term in _LOCAL_EMBEDDING_TERMS]
        vector.append(float(len(lower_text.split())) / 1_000)
        embeddings.append(vector)
    return embeddings


def _dashboard_director_record(
    director: dict[str, Any],
    supporting_chunks: list[str],
) -> dict[str, Any]:
    """Normalize director records to the Week 2 dashboard contract."""

    capacity_score = _as_float(director.get("capacity_score"), default=0.72)
    relative_load = _as_float(director.get("relative_load"), default=0.65)
    assignment_score = _as_float(
        director.get("assignment_score"),
        default=round((capacity_score * 0.45) + (0.35 if supporting_chunks else 0.15), 3),
    )
    director_name = director.get(
        "director_name",
        director.get("opportunity_owner", director.get("name", "Director A")),
    )
    capacity_label = director.get("capacity_label", "Available")
    return {
        "director_name": director_name,
        "capacity_label": capacity_label,
        "capacity_score": capacity_score,
        "relative_load": relative_load,
        "assignment_score": assignment_score,
        "match_reason": director.get(
            "match_reason",
            director.get(
                "reason",
                "Available capacity signal plus retrieved semantic examples; "
                "this does not prove prior director experience.",
            ),
        ),
        "capacity_explanation": director.get(
            "capacity_explanation",
            f"{director_name} is currently labeled {capacity_label} "
            f"with capacity score {capacity_score:.2f} and relative load {relative_load:.2f}.",
        ),
        "experience_match_explanation": director.get(
            "experience_match_explanation",
            "Prototype fit is based on the retrieved historical/sample RFP chunks.",
        ),
        "risk_flags": list(director.get("risk_flags", [])),
        "supporting_chunks": director.get("supporting_chunks", supporting_chunks[:2]),
    }


def _summarize_query(query_text: str, max_chars: int = 180) -> str:
    """Create a short fallback summary when a real summary is not available."""

    clean_text = " ".join(str(query_text).split())
    if not clean_text:
        return "Short summary of the input RFP"
    if len(clean_text) <= max_chars:
        return clean_text
    return f"{clean_text[:max_chars].rstrip()}..."


def _as_float(value: Any, default: float) -> float:
    """Convert optional numeric fields while keeping the prototype stable."""

    try:
        converted = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    if not isfinite(converted):
        return default
    return converted


def _as_int(value: Any, default: int) -> int:
    """Convert optional integer fields while keeping fallback chunks stable."""

    try:
        converted = int(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return converted

# --- Week 3 Add-ons Starts here ---
def build_chroma_from_chunks(
    chunks: list[dict],
    *,
    persist_directory: str = "data/vector_store",
    collection_name: str = "rfp_chunks",
    embedding_function=None,
    reset_collection: bool = False,
) -> "ChromaVectorStore":
    """Embed chunks and persist them into Chroma.

    chunks: dashboard-style chunk dicts (same shape accepted by build_vector_store()).
    embedding_function: callable(texts)->list[list[float]]; if None, uses Azure embed_texts().
    """
    global _LAST_CHROMA_TIMINGS
    total_start = time.perf_counter()
    timings: dict[str, Any] = {
        "reset_collection": reset_collection,
    }
    if embedding_function is None:
        try:
            from src.azure_client import embed_texts as embedding_function
        except ModuleNotFoundError:
            from azure_client import embed_texts as embedding_function

    start = time.perf_counter()
    rfp_chunks = _valid_chunks_from_dicts(chunks or [])
    texts = [chunk.text for chunk in rfp_chunks]
    timings["chroma_prepare_chunks_seconds"] = round(time.perf_counter() - start, 4)
    timings["chroma_chunk_count"] = len(rfp_chunks)

    start = time.perf_counter()
    embeddings = _embed_texts_in_batches(texts, embedding_function) if texts else []
    timings["chroma_embed_all_chunks_seconds"] = round(time.perf_counter() - start, 4)
    timings["chroma_embedding_count"] = len(embeddings)

    start = time.perf_counter()
    store = ChromaVectorStore(
        persist_directory=persist_directory,
        collection_name=collection_name,
        reset_collection=reset_collection,
    )
    timings["chroma_open_collection_seconds"] = round(time.perf_counter() - start, 4)

    start = time.perf_counter()
    store.add_chunks(rfp_chunks, embeddings)
    timings["chroma_add_chunks_seconds"] = round(time.perf_counter() - start, 4)
    timings["chroma_build_total_seconds"] = round(time.perf_counter() - total_start, 4)
    _LAST_CHROMA_TIMINGS = timings
    return store


def query_chroma(
    query_text: str,
    *,
    persist_directory: str = "data/vector_store",
    collection_name: str = "rfp_chunks",
    top_k: int = 5,
    embedding_function=None,
    require_existing_collection: bool = False,
) -> list[dict[str, Any]]:
    """Query Chroma using Azure embeddings and return dashboard-style retrieved_examples."""
    global _LAST_CHROMA_QUERY_TIMINGS
    total_start = time.perf_counter()
    timings: dict[str, Any] = {}
    if embedding_function is None:
        try:
            from src.azure_client import embed_texts as embedding_function
        except ModuleNotFoundError:
            from azure_client import embed_texts as embedding_function

    start = time.perf_counter()
    query_embedding = embedding_function([query_text])[0]
    timings["chroma_query_embedding_seconds"] = round(time.perf_counter() - start, 4)

    start = time.perf_counter()
    store = ChromaVectorStore(
        persist_directory=persist_directory,
        collection_name=collection_name,
        create_if_missing=not require_existing_collection,
    )
    timings["chroma_query_open_collection_seconds"] = round(time.perf_counter() - start, 4)

    start = time.perf_counter()
    raw = store.query(query_embedding, top_k=top_k)
    timings["chroma_collection_query_seconds"] = round(time.perf_counter() - start, 4)

    # Chroma returns dict with lists; normalize to retrieved_examples shape.
    ids = (raw.get("ids") or [[]])[0]
    docs = (raw.get("documents") or [[]])[0]
    dists = (raw.get("distances") or [[]])[0]
    metas = (raw.get("metadatas") or [[]])[0]

    out: list[dict[str, Any]] = []
    for chunk_id, doc, dist, meta in zip(ids, docs, dists, metas):
        # Many Chroma setups use distance; convert to a similarity-like score if desired.
        # Here we keep a simple monotonic transform.
        try:
            distance = float(dist)
            similarity = 1.0 / (1.0 + distance) if isfinite(distance) else None
        except (TypeError, ValueError, OverflowError):
            similarity = None

        proposal_id = None
        if isinstance(meta, dict):
            proposal_id = meta.get("proposal_id") or meta.get("document_id")

        example = {
            "proposal_id": proposal_id or "unknown",
            "chunk_id": chunk_id,
            "similarity_score": round(similarity, 4) if similarity is not None else None,
            "supporting_text": doc,
        }
        if isinstance(meta, dict):
            _copy_linkage_metadata(example, meta)
        out.append(example)

    timings["chroma_query_total_seconds"] = round(time.perf_counter() - total_start, 4)
    _LAST_CHROMA_QUERY_TIMINGS = timings
    return out
# --- Week 3 Add-ons Ends here ---


def _embed_texts_in_batches(
    texts: Sequence[str],
    embedding_function: EmbeddingFunction,
    batch_size: int = _EMBEDDING_BATCH_SIZE,
) -> list[list[float]]:
    """Embed texts in smaller batches so large corpora stay on the Azure path."""

    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    embeddings: list[list[float]] = []
    batch: list[str] = []

    for text in texts:
        batch.append(text)
        if len(batch) >= batch_size:
            embeddings.extend(embedding_function(batch))
            batch = []

    if batch:
        embeddings.extend(embedding_function(batch))

    return embeddings


def get_vector_store_status() -> dict[str, Any]:
    return {
        "local_store_ready": _DEFAULT_STORE is not None,
        "local_store_size": len(_DEFAULT_STORE) if _DEFAULT_STORE is not None else 0,
        "supports_flat_contract": True,
        "supports_chroma": True,
        "last_chroma_build_timings": dict(_LAST_CHROMA_TIMINGS),
        "last_chroma_query_timings": dict(_LAST_CHROMA_QUERY_TIMINGS),
    }


def retrieve_examples_from_chunks(
    chunks: Sequence[dict[str, Any]],
    query_text: str,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    store = build_vector_store(list(chunks or []))
    return [
        result.to_retrieved_example()
        for result in store.query(query_text, top_k=top_k)
    ]


def retrieve_examples_from_query_chunks(
    chunks: Sequence[dict[str, Any]],
    query_text: str,
    query_chunks: Sequence[dict[str, Any]] | None = None,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Retrieve examples by searching each pasted-RFP query chunk.

    The dashboard still accepts one pasted RFP text field, but long RFPs should
    not be represented by only one embedding. This helper chunks the query text
    upstream, searches each query chunk, deduplicates retrieved corpus chunks,
    and keeps the best similarity score per retrieved chunk.
    """

    store = build_vector_store(list(chunks or []))
    query_texts = _query_texts(query_text, query_chunks)
    best_by_chunk_id: dict[str, dict[str, Any]] = {}

    for query in query_texts:
        for result in store.query(query, top_k=top_k):
            example = result.to_retrieved_example()
            chunk_id = str(example.get("chunk_id") or "")
            if not chunk_id:
                continue
            previous = best_by_chunk_id.get(chunk_id)
            if previous is None or _similarity_value(example) > _similarity_value(previous):
                best_by_chunk_id[chunk_id] = example

    return sorted(
        best_by_chunk_id.values(),
        key=lambda example: (_similarity_value(example), str(example.get("chunk_id") or "")),
        reverse=True,
    )[:top_k]


def _query_texts(
    query_text: str,
    query_chunks: Sequence[dict[str, Any]] | None = None,
) -> list[str]:
    texts = [
        str(chunk.get("text") or "").strip()
        for chunk in query_chunks or []
        if isinstance(chunk, dict) and str(chunk.get("text") or "").strip()
    ]
    if texts:
        return texts
    return [str(query_text or "").strip()] if str(query_text or "").strip() else []


def _similarity_value(example: dict[str, Any]) -> float:
    try:
        value = float(example.get("similarity_score"))
    except (TypeError, ValueError, OverflowError):
        return float("-inf")
    return value if isfinite(value) else float("-inf")


_LINKAGE_METADATA_FIELDS = (
    "document_id",
    "source_type",
    "source_title",
    "rfp_alias",
    "json_s_num",
    "opportunity_id",
    "opportunity_owner",
    "opportunity_manager",
    "service_solution",
    "status",
    "status_reason",
    "opportunity_outcome",
)


def _copy_linkage_metadata(target: dict[str, Any], source: dict[str, Any]) -> None:
    for field in _LINKAGE_METADATA_FIELDS:
        value = source.get(field)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        target[field] = value
