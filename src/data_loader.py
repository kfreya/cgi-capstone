import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
CSV_DIR = DATA_DIR / "csv_files"
PROPOSALS_RESPONSES_PATH = DATA_DIR / "proposals_responses.json"


def load_proposals_responses():
    with PROPOSALS_RESPONSES_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def list_excel_files():
    return sorted(CSV_DIR.rglob("*.xlsx"))
