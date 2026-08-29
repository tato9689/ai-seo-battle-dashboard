import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "activity.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"DB inicializada en {DB_PATH}")
