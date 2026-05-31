"""Tests for Azure OpenAI client configuration helpers.

These tests avoid real Azure API calls. They use monkeypatching so local secrets
from data/.env are never required or inspected.
"""

from types import SimpleNamespace

import pytest

from src import azure_client


def _clear_azure_env(monkeypatch):
    keys = [
        "AZURE_OPENAI_API_KEY",
        "OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_EMBEDDINGS_ENDPOINT",
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
        "AZURE_OPENAI_EMBEDDING_MODEL",
        "AZURE_OPENAI_REASONING_ENDPOINT",
        "AZURE_OPENAI_CHAT_DEPLOYMENT",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)


def _disable_dotenv(monkeypatch):
    monkeypatch.setattr(azure_client, "load_dotenv", lambda *_args, **_kwargs: False)


def test_validate_azure_config_passes_with_base_env(monkeypatch):
    _clear_azure_env(monkeypatch)
    _disable_dotenv(monkeypatch)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")

    config = azure_client.validate_azure_config()

    assert config["api_key"] == "test-key"
    assert config["azure_endpoint"] == "https://example.openai.azure.com"


def test_validate_azure_config_accepts_openai_key_fallback(monkeypatch):
    _clear_azure_env(monkeypatch)
    _disable_dotenv(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "fallback-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")

    config = azure_client.validate_azure_config()

    assert config["api_key"] == "fallback-key"


def test_validate_azure_config_requires_embedding_settings(monkeypatch):
    _clear_azure_env(monkeypatch)
    _disable_dotenv(monkeypatch)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDINGS_ENDPOINT", "https://example-embeddings.openai.azure.com")

    with pytest.raises(ValueError) as exc_info:
        azure_client.validate_azure_config(require_embedding=True)

    message = str(exc_info.value)
    assert "AZURE_OPENAI_API_VERSION" in message


def test_validate_azure_config_accepts_embedding_endpoint_for_embeddings(monkeypatch):
    _clear_azure_env(monkeypatch)
    _disable_dotenv(monkeypatch)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDINGS_ENDPOINT", "https://embeddings.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "embedding-deployment")

    config = azure_client.validate_azure_config(require_embedding=True)

    assert config["azure_embedding_endpoint"] == "https://embeddings.openai.azure.com"
    assert config["embedding_model"] == "embedding-deployment"


def test_embed_texts_rejects_empty_input():
    with pytest.raises(ValueError, match="at least one"):
        azure_client.embed_texts([])


def test_get_azure_openai_client_uses_config_without_api_call(monkeypatch):
    _clear_azure_env(monkeypatch)
    _disable_dotenv(monkeypatch)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://general.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

    captured = {}

    class FakeAzureOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    client = azure_client.get_azure_openai_client(azure_openai_cls=FakeAzureOpenAI)

    assert isinstance(client, FakeAzureOpenAI)
    assert captured == {
        "api_key": "test-key",
        "azure_endpoint": "https://general.openai.azure.com",
        "api_version": "2024-02-01",
    }


def test_embed_texts_uses_embedding_endpoint_and_returns_mocked_vectors(monkeypatch):
    _clear_azure_env(monkeypatch)
    _disable_dotenv(monkeypatch)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://general.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDINGS_ENDPOINT", "https://embeddings.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")

    captured_client = {}
    captured_embedding_call = {}

    class FakeEmbeddings:
        def create(self, model, input):
            captured_embedding_call["model"] = model
            captured_embedding_call["input"] = input
            return SimpleNamespace(
                data=[
                    SimpleNamespace(embedding=[0.1, 0.2, 0.3]),
                ]
            )

    class FakeAzureOpenAI:
        def __init__(self, **kwargs):
            captured_client.update(kwargs)
            self.embeddings = FakeEmbeddings()

    monkeypatch.setattr(azure_client, "_load_azure_openai_cls", lambda: FakeAzureOpenAI)

    embeddings = azure_client.embed_texts(["hello"])

    assert embeddings == [[0.1, 0.2, 0.3]]
    assert captured_client == {
        "api_key": "test-key",
        "azure_endpoint": "https://embeddings.openai.azure.com",
        "api_version": "2024-02-01",
    }
    assert captured_embedding_call == {
        "model": "text-embedding-3-large",
        "input": ["hello"],
    }


def test_optional_embedding_helpers_when_present(monkeypatch):
    """If optional helper APIs exist, they should be fallback-safe."""

    _clear_azure_env(monkeypatch)
    _disable_dotenv(monkeypatch)

    azure_embedding_available = getattr(azure_client, "azure_embedding_available", None)
    get_embedding_function = getattr(azure_client, "get_embedding_function", None)

    if azure_embedding_available is None and get_embedding_function is None:
        pytest.skip("Optional embedding helper APIs not present in src.azure_client")

    if azure_embedding_available is not None:
        assert azure_embedding_available() is False

    if get_embedding_function is not None:
        assert get_embedding_function(prefer_azure=True) is None

    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDINGS_ENDPOINT", "https://embeddings.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")

    if azure_embedding_available is not None:
        assert azure_embedding_available() is True

    if get_embedding_function is not None:
        fn = get_embedding_function(prefer_azure=True)
        assert callable(fn)


def test_try_validate_azure_config_reports_missing_keys(monkeypatch):
    """try_validate_azure_config should return missing keys instead of raising."""

    try_validate = getattr(azure_client, "try_validate_azure_config", None)
    missing_keys = getattr(azure_client, "missing_azure_config", None)
    if try_validate is None or missing_keys is None:
        pytest.skip("Fallback-safe config helpers not present in src.azure_client")

    _clear_azure_env(monkeypatch)
    _disable_dotenv(monkeypatch)

    config, missing = try_validate(require_embedding=True)
    assert config is None
    assert isinstance(missing, list)
    assert "AZURE_OPENAI_API_VERSION" in ", ".join(missing)
    assert "AZURE_OPENAI_EMBEDDINGS_ENDPOINT" in ", ".join(missing)

    missing_direct = missing_keys(require_embedding=True)
    assert set(missing).issubset(set(missing_direct))


def test_get_azure_environment_status_reports_blocked_state(monkeypatch):
    _clear_azure_env(monkeypatch)
    _disable_dotenv(monkeypatch)

    status = azure_client.get_azure_environment_status(require_embedding=True)

    assert status["ready"] is False
    assert status["can_create_client"] is False
    assert status["can_embed"] is False
    assert "AZURE_OPENAI_API_VERSION" in status["missing"]


def test_get_azure_environment_summary_reports_ready_state(monkeypatch):
    _clear_azure_env(monkeypatch)
    _disable_dotenv(monkeypatch)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDINGS_ENDPOINT", "https://embeddings.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")

    summary = azure_client.get_azure_environment_summary(require_embedding=True)

    assert "ready" in summary.lower()


def test_can_run_azure_embedding_smoke_test_matches_embedding_availability(monkeypatch):
    _clear_azure_env(monkeypatch)
    _disable_dotenv(monkeypatch)

    assert azure_client.can_run_azure_embedding_smoke_test() is False


def test_azure_chat_available_returns_true_with_full_chat_env(monkeypatch):
    _clear_azure_env(monkeypatch)
    _disable_dotenv(monkeypatch)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://general.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")

    assert azure_client.azure_chat_available() is True


def test_azure_chat_available_returns_false_when_chat_deployment_missing(monkeypatch):
    _clear_azure_env(monkeypatch)
    _disable_dotenv(monkeypatch)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://general.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

    assert azure_client.azure_chat_available() is False


def test_chat_completion_raises_without_chat_config(monkeypatch):
    _clear_azure_env(monkeypatch)
    _disable_dotenv(monkeypatch)

    with pytest.raises(ValueError, match="Missing chat configuration"):
        azure_client.chat_completion([{"role": "user", "content": "hello"}])


def test_chat_completion_uses_general_endpoint_and_returns_content(monkeypatch):
    _clear_azure_env(monkeypatch)
    _disable_dotenv(monkeypatch)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://general.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")

    captured = {}

    class FakeCompletions:
        def create(self, model, messages, temperature, max_tokens, response_format=None):
            captured["model"] = model
            captured["messages"] = messages
            captured["response_format"] = response_format
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Test response"))]
            )

    class FakeAzureOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.chat = SimpleNamespace(completions=FakeCompletions())

    result = azure_client.chat_completion(
        [{"role": "user", "content": "hello"}],
        azure_openai_cls=FakeAzureOpenAI,
    )

    assert result == "Test response"
    assert captured["azure_endpoint"] == "https://general.openai.azure.com"
    assert captured["model"] == "gpt-4o"
    assert captured["messages"] == [{"role": "user", "content": "hello"}]
    assert captured["response_format"] == {"type": "json_object"}


def test_chat_completion_falls_back_when_json_response_format_unsupported(monkeypatch):
    _clear_azure_env(monkeypatch)
    _disable_dotenv(monkeypatch)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://general.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")

    captured = {"calls": 0}

    class FakeCompletions:
        def create(self, **kwargs):
            captured["calls"] += 1
            if "response_format" in kwargs:
                raise TypeError("response_format unsupported")
            captured["kwargs"] = kwargs
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))]
            )

    class FakeAzureOpenAI:
        def __init__(self, **_kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    result = azure_client.chat_completion(
        [{"role": "user", "content": "hello"}],
        azure_openai_cls=FakeAzureOpenAI,
    )

    assert result == "{}"
    assert captured["calls"] == 2
    assert "response_format" not in captured["kwargs"]
