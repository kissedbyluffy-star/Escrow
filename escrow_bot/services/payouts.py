from __future__ import annotations

import secrets
from datetime import datetime, timezone

from escrow_bot.services.db import db_session
from escrow_bot.services.settings import get_setting


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mock_tx_hash() -> str:
    return secrets.token_hex(16)


def enqueue_payout(
    deal_id: str,
    action: str,
    network: str,
    seller_amount: int,
    fee_amount: int,
) -> None:
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO payout_queue (
                deal_id, action, network, seller_amount_base_units, fee_amount_base_units,
                status, tries, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'QUEUED', 0, ?, ?)
            """,
            (deal_id, action, network, seller_amount, fee_amount, _now(), _now()),
        )


def process_payout_queue(mock_chain: bool, max_jobs: int = 5) -> int:
    if get_setting("PAYOUT_AUTOMATION_ON") != "1":
        return 0
    if get_setting("PAUSE_PAYOUTS") == "1":
        return 0
    processed = 0
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT * FROM payout_queue
            WHERE status IN ('QUEUED', 'FAILED')
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (max_jobs,),
        ).fetchall()
        for row in rows:
            tries = int(row["tries"]) + 1
            conn.execute(
                "UPDATE payout_queue SET status = 'PROCESSING', tries = ?, updated_at = ? WHERE id = ?",
                (tries, _now(), row["id"]),
            )
            if not mock_chain:
                conn.execute(
                    "UPDATE payout_queue SET status = 'HALTED', last_error = ?, updated_at = ? WHERE id = ?",
                    ("Signing keys missing", _now(), row["id"]),
                )
                continue
            tx_hash = _mock_tx_hash()
            conn.execute(
                "UPDATE payout_queue SET status = 'SENT', payout_tx_hash = ?, updated_at = ? WHERE id = ?",
                (tx_hash, _now(), row["id"]),
            )
            conn.execute(
                "UPDATE deals SET status = 'RELEASED', updated_at = ? WHERE deal_id = ?",
                (_now(), row["deal_id"]),
            )
            conn.execute(
                "UPDATE deals SET status = 'CLOSED', updated_at = ? WHERE deal_id = ?",
                (_now(), row["deal_id"]),
            )
            processed += 1
    return processed
