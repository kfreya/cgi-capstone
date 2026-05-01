import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / "data" / ".env"

load_dotenv(ENV_PATH)

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
AZURE_OPENAI_EMBEDDINGS_ENDPOINT = os.getenv("AZURE_OPENAI_EMBEDDINGS_ENDPOINT")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_REASONING_ENDPOINT = os.getenv("AZURE_OPENAI_REASONING_ENDPOINT")


def validate_azure_config() -> None:
    missing_config = []

    if not AZURE_OPENAI_API_KEY:
        missing_config.append("AZURE_OPENAI_API_KEY or OPENAI_API_KEY")
    if not AZURE_OPENAI_EMBEDDINGS_ENDPOINT:
        missing_config.append("AZURE_OPENAI_EMBEDDINGS_ENDPOINT")
    if not AZURE_OPENAI_ENDPOINT:
        missing_config.append("AZURE_OPENAI_ENDPOINT")
    if not AZURE_OPENAI_REASONING_ENDPOINT:
        missing_config.append("AZURE_OPENAI_REASONING_ENDPOINT")

    if missing_config:
        missing = ", ".join(missing_config)
        raise ValueError(f"Missing Azure OpenAI configuration: {missing}")


if __name__ == "__main__":
    validate_azure_config()
    print("Azure OpenAI configuration loaded successfully.")
