import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / "data" / ".env"

REQUIRED_VARIABLES = [
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_EMBEDDINGS_ENDPOINT",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_REASONING_ENDPOINT",
]


def main() -> None:
    load_dotenv(ENV_PATH)

    for variable_name in REQUIRED_VARIABLES:
        value = "FOUND" if variable_name in os.environ else "MISSING"
        print(f"{variable_name}: {value}")


if __name__ == "__main__":
    main()
