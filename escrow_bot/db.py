import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS deals (
        id TEXT PRIMARY KEY,
        buyer_id INTEGER NOT NULL,
        seller_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        deadline TEXT,
        proof_types TEXT NOT NULL,
        currency TEXT NOT NULL,
        network TEXT NOT NULL,
        amount REAL NOT NULL,
        fee_percent REAL NOT NULL,
        fee_flat REAL NOT NULL,
        status TEXT NOT NULL,
        immutable INTEGER NOT NULL,
        buyer_confirmed INTEGER NOT NULL,
        seller_confirmed INTEGER NOT NULL,
        created_by INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS payments (
        id TEXT PRIMARY KEY,
        deal_id TEXT NOT NULL,
        amount REAL NOT NULL,
        currency TEXT NOT NULL,
        network TEXT NOT NULL,
        tx_hash TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(deal_id) REFERENCES deals(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS disputes (
        id TEXT PRIMARY KEY,
        deal_id TEXT NOT NULL,
        opened_by INTEGER NOT NULL,
        reason TEXT NOT NULL,
        status TEXT NOT NULL,
        resolution TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(deal_id) REFERENCES deals(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id TEXT PRIMARY KEY,
        actor_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        deal_id TEXT,
        metadata TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
]


def connect(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    for statement in SCHEMA_STATEMENTS:
        cursor.execute(statement)
    conn.commit()


def fetch_one(conn: sqlite3.Connection, query: str, params: Iterable[Any]) -> sqlite3.Row | None:
    cursor = conn.execute(query, params)
    return cursor.fetchone()


def fetch_all(conn: sqlite3.Connection, query: str, params: Iterable[Any]) -> list[sqlite3.Row]:
    cursor = conn.execute(query, params)
    return cursor.fetchall()


def execute(conn: sqlite3.Connection, query: str, params: Iterable[Any]) -> None:
    conn.execute(query, params)
    conn.commit()


def json_dump(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def json_load(value: str) -> Any:
    return json.loads(value)
