import os
from pathlib import Path
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse, urlunparse

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
)
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-large"


def _normalize_azure_endpoint(endpoint: str) -> str:
    """Return the Azure resource root URL from a possibly fully qualified endpoint."""

    parsed = urlparse(str(endpoint or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return str(endpoint or "").strip()
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


def _infer_deployment_from_endpoint(endpoint: str) -> str:
    """Extract a deployment/model name from an Azure-style endpoint path."""

    parsed = urlparse(str(endpoint or "").strip())
    parts = [part for part in parsed.path.split("/") if part]
    if "deployments" in parts:
        deployment_index = parts.index("deployments") + 1
        if deployment_index < len(parts):
            return parts[deployment_index]
    return ""


def _get_embedding_model() -> str:
    """Return the embedding model/deployment name for Azure embeddings."""

    return (
        os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        or os.getenv("AZURE_OPENAI_EMBEDDING_MODEL")
        or _infer_deployment_from_endpoint(os.getenv("AZURE_OPENAI_EMBEDDINGS_ENDPOINT", ""))
        or DEFAULT_EMBEDDING_MODEL
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
            "embedding_model": _get_embedding_model(),
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
        "embedding_model": _get_embedding_model(),
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
        azure_endpoint=_normalize_azure_endpoint(config["azure_endpoint"]),
        api_version=config["api_version"],
    )


def get_azure_embedding_client(azure_openai_cls=None):
    """Create an Azure OpenAI SDK client for embedding calls."""

    config = validate_azure_config(require_embedding=True)
    azure_openai_cls = azure_openai_cls or _load_azure_openai_cls()
    return azure_openai_cls(
        api_key=config["api_key"],
        azure_endpoint=_normalize_azure_endpoint(config["azure_embedding_endpoint"]),
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
        model=config["embedding_model"],
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


def get_azure_environment_status(require_embedding: bool = True) -> dict[str, Any]:
    config, missing = try_validate_azure_config(require_embedding=require_embedding)
    return {
        "ready": config is not None,
        "require_embedding": require_embedding,
        "missing": missing,
        "can_create_client": config is not None,
        "can_embed": config is not None and require_embedding,
    }


def get_azure_environment_summary(require_embedding: bool = True) -> str:
    status = get_azure_environment_status(require_embedding=require_embedding)
    if status["ready"]:
        return "Azure OpenAI configuration is ready."
    if status["missing"]:
        return "Azure OpenAI configuration is blocked: " + ", ".join(status["missing"])
    return "Azure OpenAI configuration is blocked."


def can_run_azure_embedding_smoke_test() -> bool:
    return azure_embedding_available()

# --- Week 3 Add-ons Ends here ---


# --- Week 4 Chat Add-ons Starts here ---
def azure_chat_available() -> bool:
    """Return True if chat config looks usable (no API call)."""
    load_dotenv(ENV_PATH)
    return bool(
        (os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"))
        and os.getenv("AZURE_OPENAI_ENDPOINT")
        and os.getenv("AZURE_OPENAI_API_VERSION")
        and os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
    )


def chat_completion(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int = 1200,
    azure_openai_cls=None,
) -> str:
    """Call the Azure OpenAI chat deployment and return the response text.

    @param messages: Chat messages as list of role/content dicts.
    @param temperature: Sampling temperature.
    @param max_tokens: Maximum response tokens.
    @return: Response message content as a string.
    @raises ValueError: If required configuration is missing.
    """
    load_dotenv(ENV_PATH)
    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "")
    chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "")
    missing = [
        k
        for k, v in {
            "AZURE_OPENAI_API_KEY": api_key,
            "AZURE_OPENAI_ENDPOINT": azure_endpoint,
            "AZURE_OPENAI_API_VERSION": api_version,
            "AZURE_OPENAI_CHAT_DEPLOYMENT": chat_deployment,
        }.items()
        if not v
    ]
    if missing:
        raise ValueError(f"Missing chat configuration: {', '.join(missing)}")
    azure_openai_cls = azure_openai_cls or _load_azure_openai_cls()
    client = azure_openai_cls(
        api_key=api_key,
        azure_endpoint=_normalize_azure_endpoint(azure_endpoint),
        api_version=api_version,
    )
    request = {
        "model": chat_deployment,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    try:
        response = client.chat.completions.create(**request)
    except TypeError:
        request.pop("response_format", None)
        response = client.chat.completions.create(**request)
    return response.choices[0].message.content or ""

# --- Week 4 Chat Add-ons Ends here ---
