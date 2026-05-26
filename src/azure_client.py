import os
from pathlib import Path
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

try:
    from dotenv import load_dotenv  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:  # type: ignore
        return False

if TYPE_CHECKING:  # pragma: no cover
    from openai import AzureOpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / "data" / ".env"

BASE_CONFIG_KEYS = (
    "AZURE_OPENAI_ENDPOINT",
)
EMBEDDING_CONFIG_KEYS = (
    "AZURE_OPENAI_EMBEDDINGS_ENDPOINT",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
)

def missing_azure_config(require_embedding: bool = False) -> list[str]:
    """Return missing Azure OpenAI configuration keys (does not raise).

    This helper is intended for fallback-safe code paths (dashboard/UI). It can
    be called even when Azure is not configured and should never make an API
    call.
    """

    load_dotenv(ENV_PATH)

    missing: list[str] = []

    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        missing.append("AZURE_OPENAI_API_KEY or OPENAI_API_KEY")

    if require_embedding:
        for key in EMBEDDING_CONFIG_KEYS:
            if not os.getenv(key):
                missing.append(key)
    else:
        for key in BASE_CONFIG_KEYS:
            if not os.getenv(key):
                missing.append(key)

    return missing


def try_validate_azure_config(require_embedding: bool = False) -> tuple[dict[str, str] | None, list[str]]:
    """Best-effort config validation that never raises.

    @return: (config_or_none, missing_keys)
    """

    missing = missing_azure_config(require_embedding=require_embedding)
    if missing:
        return None, missing

    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    return (
        {
            "api_key": api_key or "",
            "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            "azure_embedding_endpoint": os.getenv("AZURE_OPENAI_EMBEDDINGS_ENDPOINT", ""),
            "api_version": os.getenv("AZURE_OPENAI_API_VERSION", ""),
            "embedding_deployment": os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", ""),
        },
        [],
    )


def validate_azure_config(require_embedding: bool = False) -> dict[str, str]:
    """Validate Azure OpenAI environment configuration.

    @param require_embedding: When true, require embedding-specific SDK config.
    @return: Sanitized config dictionary for Azure OpenAI helpers.
    @raises ValueError: If required configuration is missing.
    """

    load_dotenv(ENV_PATH)

    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    config = {
        "api_key": api_key or "",
        "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        "azure_embedding_endpoint": os.getenv("AZURE_OPENAI_EMBEDDINGS_ENDPOINT", ""),
        "api_version": os.getenv("AZURE_OPENAI_API_VERSION", ""),
        "embedding_deployment": os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", ""),
    }

    missing_config = missing_azure_config(require_embedding=require_embedding)

    if missing_config:
        missing = ", ".join(missing_config)
        raise ValueError(f"Missing Azure OpenAI configuration: {missing}")

    return config


def _load_azure_openai_cls():
    """Import AzureOpenAI lazily so helpers stay importable without the SDK."""

    try:
        from openai import AzureOpenAI  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ModuleNotFoundError(
            "openai SDK is required to create an AzureOpenAI client. "
            "Install project dependencies before using get_azure_openai_client/embed_texts."
        ) from exc
    return AzureOpenAI


def get_azure_openai_client(azure_openai_cls=None):
    """Create an Azure OpenAI SDK client without making an API call."""

    config = validate_azure_config(require_embedding=False)
    azure_openai_cls = azure_openai_cls or _load_azure_openai_cls()
    return azure_openai_cls(
        api_key=config["api_key"],
        azure_endpoint=config["azure_endpoint"],
        api_version=config["api_version"],
    )


def get_azure_embedding_client(azure_openai_cls=None):
    """Create an Azure OpenAI SDK client for embedding calls."""

    config = validate_azure_config(require_embedding=True)
    azure_openai_cls = azure_openai_cls or _load_azure_openai_cls()
    return azure_openai_cls(
        api_key=config["api_key"],
        azure_endpoint=config["azure_embedding_endpoint"],
        api_version=config["api_version"],
    )


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """Embed text with the configured Azure OpenAI embedding deployment.

    @param texts: Non-empty sequence of text strings to embed.
    @return: Embedding vectors in the same order as the input texts.
    @raises ValueError: If no texts are provided.
    """

    if not texts:
        raise ValueError("texts must contain at least one item")

    config = validate_azure_config(require_embedding=True)
    client = get_azure_embedding_client()
    response = client.embeddings.create(
        model=config["embedding_deployment"],
        input=list(texts),
    )
    return [list(item.embedding) for item in response.data]


if __name__ == "__main__":
    validate_azure_config()
    print("Azure OpenAI configuration loaded successfully.")


# --- Week 3 Add-ons Starts here---
def azure_embedding_available() -> bool:
    """Return True if embedding config looks usable (no API call)."""
    return not missing_azure_config(require_embedding=True)


def get_embedding_function(prefer_azure: bool = True):
    """Return an embedding function(texts)->embeddings with safe fallback.

    - If prefer_azure and Azure env is present, returns embed_texts (real Azure call).
    - Otherwise returns None so caller can fall back to local embeddings.
    """
    if prefer_azure and azure_embedding_available():
        return embed_texts
    return None

# --- Week 3 Add-ons Ends here ---
