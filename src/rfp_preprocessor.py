"""Preprocess historical RFP proposals for retrieval-augmented generation.

The real project data is sensitive, so this module keeps the assumptions about
the JSON structure small and explicit. It converts proposal/response records
into plain-text documents, then creates overlapping chunks that can be embedded
and stored in a vector database.

Run project files from the repository root so imports resolve consistently.
For example: `python src/rfp_preprocessor.py`.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_CHUNK_SIZE = 500
DEFAULT_OVERLAP = 50
DEFAULT_PROPOSAL_JSON_PATH = Path("data/proposals_responses.json")
SAMPLE_RFP_TEXT = (
    "CGI is responding to a request for cloud migration, data analytics, "
    "dashboard reporting, and managed service support. The work includes "
    "planning, delivery coordination, risk tracking, and executive reporting."
)
TOKEN_PATTERN = re.compile(r"\S+")


@dataclass(frozen=True)
class RFPDocument:
    """A proposal or proposal-response text unit before chunking.

    @param document_id: Stable ID for this source document.
    @param title: Original RFP title from the proposal JSON.
    @param section: Whether this is the proposal text or a response section.
    @param text: Normalized text that will later be chunked.
    @param metadata: Source information to keep retrieval results traceable.
    """

    document_id: str
    title: str
    section: str
    text: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert the document to a plain dictionary.

        @return: Dictionary version of the document for logging or JSON output.
        """

        return asdict(self)


@dataclass(frozen=True)
class RFPChunk:
    """A retrieval-ready text chunk with enough metadata to trace its source.

    @param chunk_id: Stable ID for this chunk.
    @param document_id: ID of the document this chunk came from.
    @param title: Original RFP title from the proposal JSON.
    @param section: Proposal or response section name.
    @param chunk_index: Position of this chunk within its source document.
    @param text: Chunk text that will be embedded.
    @param metadata: Source and span information for retrieval explanations.
    """

    chunk_id: str
    document_id: str
    title: str
    section: str
    chunk_index: int
    text: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert the chunk to a plain dictionary.

        @return: Dictionary version of the chunk for storage or API output.
        """

        return asdict(self)


@dataclass(frozen=True)
class _ChunkSpan:
    """Internal representation of a chunk plus its source offsets."""

    text: str
    start_char: int
    end_char: int
    start_token: int
    end_token: int


def normalize_text_content(content: Any) -> str:
    """Convert JSON content fields into plain text.

    The proposal data can store text as a string, a list of paragraphs, or a
    small dictionary with a `content` field. This helper gives the rest of the
    pipeline one consistent string representation.

    @param content: Raw content value from the proposal JSON.
    @return: Clean plain text with empty parts removed.
    """

    if content is None:
        return ""

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, Mapping):
        if "content" in content:
            return normalize_text_content(content["content"])
        # Some synthetic/local records may contain nested text dictionaries.
        return "\n".join(
            part for value in content.values() if (part := normalize_text_content(value))
        )

    if isinstance(content, Sequence) and not isinstance(content, (bytes, bytearray)):
        return "\n".join(
            part for item in content if (part := normalize_text_content(item))
        )

    return str(content).strip()


def extract_rfp_documents(proposals: Mapping[str, Any]) -> list[RFPDocument]:
    """Extract proposal and response documents from the historical RFP JSON.

    Each RFP can contribute more than one document: the original proposal text
    and zero or more historical response sections. Keeping them separate makes
    retrieval more interpretable later because each chunk still knows whether it
    came from the request or from a response.

    @param proposals: Mapping from RFP title to proposal record.
    @return: List of normalized proposal and response documents.
    @raises TypeError: If `proposals` is not a mapping.
    """

    if not isinstance(proposals, Mapping):
        raise TypeError("proposals must be a mapping of RFP titles to records")

    documents: list[RFPDocument] = []

    for proposal_index, (title, entry) in enumerate(proposals.items()):
        if not isinstance(entry, Mapping):
            continue

        proposal = entry.get("proposal", entry)
        if not isinstance(proposal, Mapping):
            continue

        base_document_id = _safe_id(title) or f"proposal_{proposal_index}"
        proposal_text = normalize_text_content(proposal.get("content"))

        if proposal_text:
            documents.append(
                RFPDocument(
                    document_id=f"{base_document_id}__proposal",
                    title=str(title),
                    section="proposal",
                    text=proposal_text,
                    metadata={
                        "proposal_id": base_document_id,
                        "source_title": str(title),
                        "source_type": "proposal",
                        "proposal_index": proposal_index,
                        "opportunity_owner": None,
                        "opportunity_id": None,
                    },
                )
            )

        documents.extend(
            _extract_response_documents(
                title=str(title),
                proposal=proposal,
                base_document_id=base_document_id,
                proposal_index=proposal_index,
            )
        )

    return documents


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """Split text into overlapping token-like chunks.

    Long RFPs need to be split before embedding. The overlap keeps a little bit
    of context from the previous chunk so important details are less likely to
    be cut off at a chunk boundary.

    @param text: Source text to split.
    @param chunk_size: Maximum approximate tokens per chunk.
    @param overlap: Approximate tokens repeated between chunks.
    @return: List of chunk strings.
    @raises ValueError: If the chunk size settings are invalid.
    """

    return [
        span.text
        for span in _chunk_text_with_spans(
            text=text,
            chunk_size=chunk_size,
            overlap=overlap,
        )
    ]


def chunk_rfp_documents(
    documents: Sequence[RFPDocument],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[RFPChunk]:
    """Chunk extracted RFP documents and preserve retrieval metadata.

    This is the main bridge between cleaned proposal text and vector search.
    The output chunks include enough metadata to show which RFP and section a
    retrieved result came from.

    @param documents: Extracted proposal/response documents.
    @param chunk_size: Maximum approximate tokens per chunk.
    @param overlap: Approximate tokens repeated between chunks.
    @return: Retrieval-ready RFP chunks.
    """

    chunks: list[RFPChunk] = []

    for document in documents:
        spans = _chunk_text_with_spans(
            document.text,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for chunk_index, span in enumerate(spans):
            chunk_id = f"{document.document_id}__chunk_{chunk_index:04d}"
            proposal_id = str(
                document.metadata.get("proposal_id", document.document_id)
            )
            chunks.append(
                RFPChunk(
                    chunk_id=chunk_id,
                    document_id=document.document_id,
                    title=document.title,
                    section=document.section,
                    chunk_index=chunk_index,
                    text=span.text,
                    metadata={
                        **document.metadata,
                        "proposal_id": proposal_id,
                        "chunk_id": chunk_id,
                        "source_type": document.metadata.get(
                            "source_type",
                            document.section,
                        ),
                        "opportunity_owner": document.metadata.get(
                            "opportunity_owner"
                        ),
                        "opportunity_id": document.metadata.get("opportunity_id"),
                        # Span metadata helps debug retrieval and explain sources.
                        "chunk_index": chunk_index,
                        "chunk_start_char": span.start_char,
                        "chunk_end_char": span.end_char,
                        "chunk_start_token": span.start_token,
                        "chunk_end_token": span.end_token,
                        "approx_tokens": span.end_token - span.start_token,
                    },
                )
            )

    return chunks


def preprocess_proposals(
    proposals: Mapping[str, Any],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[RFPChunk]:
    """Run the full preprocessing path from proposal JSON to RFP chunks.

    This is the easiest function to call for preprocessing: load the proposal
    JSON, pass it here, then embed the returned chunks.

    @param proposals: Mapping from RFP title to proposal record.
    @param chunk_size: Maximum approximate tokens per chunk.
    @param overlap: Approximate tokens repeated between chunks.
    @return: Retrieval-ready chunks for embedding.
    """

    documents = extract_rfp_documents(proposals)
    return chunk_rfp_documents(
        documents,
        chunk_size=chunk_size,
        overlap=overlap,
    )


def prepare_rfp_chunks(rfp_text: str) -> list[dict]:
    """Prepare pasted RFP text for the dashboard retrieval interface.

    This wrapper matches the Role 5 dashboard contract. It uses the same
    chunking logic as the historical proposal pipeline, but the input is one
    new RFP text string instead of the full proposals JSON.

    @param rfp_text: New RFP text pasted or uploaded in the dashboard.
    @return: List of flat chunk dictionaries for vector-store input.
    """

    spans = _chunk_text_with_spans(
        normalize_text_content(rfp_text),
        chunk_size=DEFAULT_CHUNK_SIZE,
        overlap=DEFAULT_OVERLAP,
    )

    return [
        {
            "proposal_id": "proposal_001",
            "chunk_id": f"proposal_001_chunk_{chunk_index + 1:03d}",
            "source_type": "proposal",
            "text": span.text,
            "chunk_index": chunk_index,
            "opportunity_owner": None,
            "opportunity_id": None,
        }
        for chunk_index, span in enumerate(spans)
    ]


def load_sample_rfp_text(
    json_path: str | Path = DEFAULT_PROPOSAL_JSON_PATH,
) -> str:
    """Load one sample RFP/proposal text for the independent prototype.

    The real proposal JSON is private and may not exist in every local checkout.
    If the file is missing or difficult to parse, this returns a synthetic RFP
    paragraph so the Week 2 pipeline can still run end to end.

    @param json_path: Local path to `proposals_responses.json`.
    @return: Real sample proposal text when available, otherwise synthetic text.
    """

    path = Path(json_path)
    if not path.exists():
        return SAMPLE_RFP_TEXT

    try:
        with path.open(encoding="utf-8") as json_file:
            proposals = json.load(json_file)
    except (OSError, json.JSONDecodeError):
        return SAMPLE_RFP_TEXT

    if not isinstance(proposals, Mapping):
        return SAMPLE_RFP_TEXT

    documents = extract_rfp_documents(proposals)
    if not documents:
        return SAMPLE_RFP_TEXT
    return documents[0].text


def estimate_token_count(text: str) -> int:
    """Return the same approximate token count used by the chunker.

    This is not a model tokenizer. It is a lightweight estimate for local
    preprocessing and tests.

    @param text: Text to count.
    @return: Number of whitespace-based token-like spans.
    """

    return len(TOKEN_PATTERN.findall(" ".join(text.split())))


def _extract_response_documents(
    title: str,
    proposal: Mapping[str, Any],
    base_document_id: str,
    proposal_index: int,
) -> list[RFPDocument]:
    """Extract response sections for one proposal record.

    @param title: Original RFP title.
    @param proposal: Proposal dictionary containing response data.
    @param base_document_id: Safe ID prefix for this RFP.
    @param proposal_index: Position of the RFP in the source mapping.
    @return: Normalized response documents for this proposal.
    """

    responses = proposal.get("proposal_response", proposal.get("proposal_responses", {}))
    response_items = _iter_response_items(responses)
    documents: list[RFPDocument] = []

    for response_index, (response_name, response) in enumerate(response_items):
        response_text = normalize_text_content(response)
        if not response_text:
            continue

        response_id = _safe_id(response_name) or f"response_{response_index}"
        documents.append(
            RFPDocument(
                document_id=f"{base_document_id}__response__{response_id}",
                title=title,
                section=f"response:{response_name}",
                text=response_text,
                metadata={
                    "proposal_id": base_document_id,
                    "source_title": title,
                    "source_type": "proposal_response",
                    "response_name": str(response_name),
                    "proposal_index": proposal_index,
                    "response_index": response_index,
                    "opportunity_owner": None,
                    "opportunity_id": None,
                },
            )
        )

    return documents


def _iter_response_items(responses: Any) -> list[tuple[str, Any]]:
    """Return response records as `(name, content)` pairs.

    @param responses: Raw response value from the proposal JSON.
    @return: Named response items, or an empty list if the shape is unsupported.
    """

    if isinstance(responses, Mapping):
        return list(responses.items())

    if isinstance(responses, Sequence) and not isinstance(
        responses,
        (str, bytes, bytearray),
    ):
        return [(f"response_{index}", response) for index, response in enumerate(responses)]

    return []


def _chunk_text_with_spans(
    text: str,
    chunk_size: int,
    overlap: int,
) -> list[_ChunkSpan]:
    """Split text into chunks and keep character/token offsets.

    @param text: Source text to split.
    @param chunk_size: Maximum approximate tokens per chunk.
    @param overlap: Approximate tokens repeated between chunks.
    @return: Chunk spans containing text and source offsets.
    """

    _validate_chunk_settings(chunk_size=chunk_size, overlap=overlap)

    clean_text = " ".join(str(text).split())
    token_matches = list(TOKEN_PATTERN.finditer(clean_text))

    if not token_matches:
        return []

    spans: list[_ChunkSpan] = []
    start_token = 0
    step = chunk_size - overlap

    while start_token < len(token_matches):
        end_token = min(start_token + chunk_size, len(token_matches))
        start_char = token_matches[start_token].start()
        end_char = token_matches[end_token - 1].end()

        spans.append(
            _ChunkSpan(
                text=clean_text[start_char:end_char],
                start_char=start_char,
                end_char=end_char,
                start_token=start_token,
                end_token=end_token,
            )
        )

        if end_token == len(token_matches):
            break
        # Move forward by less than chunk_size so the next chunk overlaps.
        start_token += step

    return spans


def _validate_chunk_settings(chunk_size: int, overlap: int) -> None:
    """Validate chunk size settings before splitting text.

    @param chunk_size: Maximum approximate tokens per chunk.
    @param overlap: Approximate tokens repeated between chunks.
    @raises ValueError: If either value would make chunking invalid.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap cannot be negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")


def _safe_id(value: Any) -> str:
    """Convert a title or section name into a stable lowercase ID.

    @param value: Raw value to convert.
    @return: Safe ID containing lowercase alphanumeric parts and underscores.
    """

    safe = "".join(
        character.lower() if character.isalnum() else "_"
        for character in str(value).strip()
    )
    return "_".join(part for part in safe.split("_") if part)


def _preview_chunk(chunk: dict[str, Any], max_chars: int = 500) -> str:
    """Format one chunk so it is readable when running this file directly.

    @param chunk: Flat chunk dictionary from `prepare_rfp_chunks()`.
    @param max_chars: Maximum number of text characters to print.
    @return: Multi-line preview string for the terminal.
    """

    text_preview = str(chunk.get("text", "")).strip()
    if len(text_preview) > max_chars:
        text_preview = f"{text_preview[:max_chars].rstrip()}..."

    return "\n".join(
        [
            f"Chunk ID: {chunk.get('chunk_id')}",
            f"Proposal ID: {chunk.get('proposal_id')}",
            f"Source type: {chunk.get('source_type')}",
            f"Chunk index: {chunk.get('chunk_index')}",
            f"Opportunity owner: {chunk.get('opportunity_owner')}",
            f"Opportunity ID: {chunk.get('opportunity_id')}",
            "",
            "Text preview:",
            text_preview,
        ]
    )


def _run_demo() -> None:
    """Print a small readable preprocessing preview for local checks."""

    sample_text = load_sample_rfp_text()
    chunks = prepare_rfp_chunks(sample_text)

    print("RFP preprocessing demo")
    print(f"Sample text characters: {len(sample_text)}")
    print(f"Generated chunks: {len(chunks)}")

    if chunks:
        print()
        print(_preview_chunk(chunks[0]))


if __name__ == "__main__":
    _run_demo()
