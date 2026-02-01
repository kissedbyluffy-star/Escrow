from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

def _db_path() -> Path:
    return Path(os.getenv("ESCROW_DB_PATH", "data/escrow.db"))


def _connect() -> sqlite3.Connection:
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db_session() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                first_seen_at TEXT,
                is_human_verified INTEGER DEFAULT 0,
                verified_at TEXT,
                risk_score INTEGER DEFAULT 0,
                is_flagged INTEGER DEFAULT 0,
                trust_tier TEXT DEFAULT 'standard',
                locked_until TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS terms_acceptance (
                tg_id INTEGER PRIMARY KEY,
                terms_version TEXT NOT NULL,
                accepted_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS deals (
                deal_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                terms TEXT NOT NULL,
                proof_requirements TEXT NOT NULL,
                deadline TEXT,
                amount_base_units INTEGER NOT NULL,
                display_amount TEXT NOT NULL,
                asset TEXT NOT NULL,
                network TEXT NOT NULL,
                buyer_tg_id INTEGER NOT NULL,
                buyer_username_snapshot TEXT,
                seller_tg_id INTEGER NOT NULL,
                seller_username_snapshot TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS deposits (
                deal_id TEXT NOT NULL,
                tx_hash TEXT NOT NULL UNIQUE,
                to_addr TEXT NOT NULL,
                amount_base_units INTEGER NOT NULL,
                confirmations INTEGER NOT NULL,
                detected_at TEXT NOT NULL,
                raw_json TEXT,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
            );
            CREATE TABLE IF NOT EXISTS payout_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                action TEXT NOT NULL,
                network TEXT NOT NULL,
                seller_amount_base_units INTEGER NOT NULL,
                fee_amount_base_units INTEGER NOT NULL,
                status TEXT NOT NULL,
                tries INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                payout_tx_hash TEXT,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS group_pool (
                chat_id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                current_deal_id TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS waitlist (
                deal_id TEXT PRIMARY KEY,
                requested_at TEXT NOT NULL,
                mode TEXT NOT NULL
            );
            """
        )
