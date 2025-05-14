
"""Database helper for AI Agent (SQLite v1)"""
import sqlite3
from pathlib import Path
import datetime

SCHEMA_VERSION = 1

CREATE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS instances (
        instance_id            TEXT PRIMARY KEY,
        original_instance_path TEXT NOT NULL UNIQUE,
        status                 TEXT NOT NULL CHECK(status IN ('pending','processing','paused','error','done')),
        step_index             INTEGER NOT NULL DEFAULT 0,
        error_message          TEXT,
        input_path             TEXT NOT NULL,
        output_path            TEXT,
        parent_instance_id     TEXT REFERENCES instances(instance_id),
        created_at             TEXT NOT NULL,
        updated_at             TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS history_entries (
        entry_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        instance_id  TEXT NOT NULL REFERENCES instances(instance_id),
        step_name    TEXT NOT NULL,
        status       TEXT NOT NULL,
        start_time   TEXT NOT NULL,
        end_time     TEXT,
        details      TEXT
    );
    """,
    """CREATE INDEX IF NOT EXISTS idx_instances_status ON instances(status);""",
    """CREATE INDEX IF NOT EXISTS idx_instances_parent_id ON instances(parent_instance_id);""",
    """CREATE INDEX IF NOT EXISTS idx_history_instance_id ON history_entries(instance_id);"""
]

def initialize_db(db_path: Path) -> None:
    """Initialise the SQLite database with the required schema if it doesn't exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        cur = conn.cursor()
        for stmt in CREATE_STATEMENTS:
            cur.execute(stmt)
        conn.commit()

def get_connection(db_path: Path) -> sqlite3.Connection:
    """Return a SQLite connection, ensuring the DB exists."""
    initialize_db(db_path)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
