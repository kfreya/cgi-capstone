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
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
        "AZURE_OPENAI_EMBEDDINGS_ENDPOINT",
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

    with pytest.raises(ValueError) as exc_info:
        azure_client.validate_azure_config(require_embedding=True)

    message = str(exc_info.value)
    assert "AZURE_OPENAI_API_VERSION" in message
    assert "AZURE_OPENAI_EMBEDDING_DEPLOYMENT" in message


def test_embed_texts_rejects_empty_input():
    with pytest.raises(ValueError, match="at least one"):
        azure_client.embed_texts([])


def test_get_azure_openai_client_uses_config_without_api_call(monkeypatch):
    _clear_azure_env(monkeypatch)
    _disable_dotenv(monkeypatch)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "embedding-deployment")

    captured = {}

    class FakeAzureOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(azure_client, "AzureOpenAI", FakeAzureOpenAI)

    client = azure_client.get_azure_openai_client()

    assert isinstance(client, FakeAzureOpenAI)
    assert captured == {
        "api_key": "test-key",
        "azure_endpoint": "https://example.openai.azure.com",
        "api_version": "2024-02-01",
    }


def test_embed_texts_returns_mocked_vectors(monkeypatch):
    _clear_azure_env(monkeypatch)
    _disable_dotenv(monkeypatch)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "embedding-deployment")

    captured = {}

    class FakeEmbeddings:
        def create(self, model, input):
            captured["model"] = model
            captured["input"] = input
            return SimpleNamespace(
                data=[
                    SimpleNamespace(embedding=[0.1, 0.2, 0.3]),
                ]
            )

    class FakeClient:
        embeddings = FakeEmbeddings()

    monkeypatch.setattr(azure_client, "get_azure_openai_client", lambda: FakeClient())

    embeddings = azure_client.embed_texts(["hello"])

    assert embeddings == [[0.1, 0.2, 0.3]]
    assert captured == {
        "model": "embedding-deployment",
        "input": ["hello"],
    }
