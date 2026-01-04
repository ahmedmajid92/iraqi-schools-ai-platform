import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS study_plans (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  title TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reading_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  label TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quiz_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  kind TEXT NOT NULL,
  payload_json TEXT NOT NULL
);
"""

def init_db(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()

@contextmanager
def db_conn(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def insert_json(db_path: str, table: str, created_at: str, label_or_kind: str, payload_json: str) -> int:
    col = "title" if table == "study_plans" else ("label" if table == "reading_results" else "kind")
    sql = f"INSERT INTO {table} (created_at, {col}, payload_json) VALUES (?, ?, ?)"
    with db_conn(db_path) as conn:
        cur = conn.execute(sql, (created_at, label_or_kind, payload_json))
        return int(cur.lastrowid)

def list_rows(db_path: str, table: str, limit: int = 10) -> List[Dict[str, Any]]:
    sql = f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?"
    with db_conn(db_path) as conn:
        rows = conn.execute(sql, (limit,)).fetchall()
        return [dict(r) for r in rows]

def get_row(db_path: str, table: str, row_id: int) -> Optional[Dict[str, Any]]:
    sql = f"SELECT * FROM {table} WHERE id = ?"
    with db_conn(db_path) as conn:
        r = conn.execute(sql, (row_id,)).fetchone()
        return dict(r) if r else None
