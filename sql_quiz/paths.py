"""Repository asset paths, independent of the process working directory."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
CSV_DIR = DATA_DIR / "chinook"
SCHEMA_PATH = DATA_DIR / "schema.json"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
KNOWLEDGE_PATH = PROJECT_ROOT / "knowledge" / "documents.jsonl"
SQL_DIR = PROJECT_ROOT / "sql"
