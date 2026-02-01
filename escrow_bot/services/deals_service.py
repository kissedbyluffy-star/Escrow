from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone

from escrow_bot.services.db import db_session
from escrow_bot.utils.state_machine import ensure_transition

ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_deal_id() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(8))


def create_deal(payload: dict) -> str:
    deal_id = _generate_deal_id()
    payload = payload.copy()
    payload["deal_id"] = deal_id
    payload["created_at"] = _now()
    payload["updated_at"] = payload["created_at"]
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO deals (
                deal_id, title, terms, proof_requirements, deadline, amount_base_units,
                display_amount, asset, network, buyer_tg_id, buyer_username_snapshot,
                seller_tg_id, seller_username_snapshot, status, created_at, updated_at
            ) VALUES (
                :deal_id, :title, :terms, :proof_requirements, :deadline,
                :amount_base_units, :display_amount, :asset, :network, :buyer_tg_id,
                :buyer_username_snapshot, :seller_tg_id, :seller_username_snapshot,
                :status, :created_at, :updated_at
            )
            """,
            payload,
        )
    return deal_id


def list_deals_for_user(tg_id: int, limit: int = 10) -> list[dict]:
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT deal_id, title, status FROM deals
            WHERE buyer_tg_id = ? OR seller_tg_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (tg_id, tg_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def get_deal(deal_id: str) -> dict | None:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM deals WHERE deal_id = ?", (deal_id,)).fetchone()
    return dict(row) if row else None


def update_deal_status(deal_id: str, new_status: str) -> None:
    deal = get_deal(deal_id)
    if not deal:
        raise KeyError("Deal not found")
    ensure_transition(deal["status"], new_status)
    with db_session() as conn:
        conn.execute(
            "UPDATE deals SET status = ?, updated_at = ? WHERE deal_id = ?",
            (new_status, _now(), deal_id),
        )


def add_deposit(
    deal_id: str,
    tx_hash: str,
    to_addr: str,
    amount_base_units: int,
    confirmations: int,
    raw_json: dict | None = None,
) -> None:
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO deposits (deal_id, tx_hash, to_addr, amount_base_units, confirmations,
                detected_at, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                deal_id,
                tx_hash,
                to_addr,
                amount_base_units,
                confirmations,
                _now(),
                json.dumps(raw_json) if raw_json else None,
            ),
        )
