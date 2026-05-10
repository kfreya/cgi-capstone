"""Vector retrieval utilities for the RFP assignment workflow.

This file keeps embedding generation separate from retrieval. In local tests we
can pass a small fake embedding function; in production the same interface can
wrap Azure OpenAI embeddings before writing to Chroma.

Run project files from the repository root so imports resolve consistently.
For example: `python src/vector_store.py`.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from math import sqrt
from typing import Any

try:
    from src.rfp_preprocessor import RFPChunk
except ModuleNotFoundError:
    # Allows `python vector_store.py` while working directly inside the src folder.
    from rfp_preprocessor import RFPChunk


EmbeddingFunction = Callable[[Sequence[str]], list[list[float]]]


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
    ) -> None:
        """Connect to a persistent Chroma collection.

        @param persist_directory: Local directory for Chroma vector-store files.
        @param collection_name: Chroma collection name for RFP chunks.
        @raises ImportError: If `chromadb` is not installed.
        """

        try:
            import chromadb
        except ImportError as exc:
            raise ImportError(
                "chromadb is required for ChromaVectorStore. "
                "Install the project environment before using it."
            ) from exc

        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name=collection_name)

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
    notes: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Create a stable mock output shape for downstream dashboard work.

    @param query_text: New RFP text or short query used for retrieval.
    @param results: Retrieved chunks that support the recommendation.
    @param rfp_summary: Optional summary of the new RFP.
    @param recommended_directors: Optional director ranking records.
    @param notes: Optional notes about assumptions or missing data.
    @return: Dictionary shaped like the future dashboard/API response.
    """

    return {
        "rfp_summary": rfp_summary,
        "query_text": query_text,
        "recommended_directors": list(recommended_directors or []),
        "supporting_chunks": [result.to_dict() for result in results],
        "notes": list(notes or []),
    }


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
