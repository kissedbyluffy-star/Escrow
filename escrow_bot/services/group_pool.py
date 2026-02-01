from __future__ import annotations

from datetime import datetime, timezone

from escrow_bot.services.db import db_session


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_group(chat_id: int) -> None:
    with db_session() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO group_pool (chat_id, status, current_deal_id, updated_at) "
            "VALUES (?, 'AVAILABLE', NULL, ?)",
            (chat_id, _now()),
        )


def allocate_group(deal_id: str) -> int | None:
    with db_session() as conn:
        row = conn.execute(
            "SELECT chat_id FROM group_pool WHERE status = 'AVAILABLE' LIMIT 1"
        ).fetchone()
        if not row:
            return None
        chat_id = int(row["chat_id"])
        conn.execute(
            "UPDATE group_pool SET status = 'IN_USE', current_deal_id = ?, updated_at = ? "
            "WHERE chat_id = ?",
            (deal_id, _now(), chat_id),
        )
        return chat_id


def release_group(chat_id: int) -> None:
    with db_session() as conn:
        conn.execute(
            "UPDATE group_pool SET status = 'AVAILABLE', current_deal_id = NULL, updated_at = ? "
            "WHERE chat_id = ?",
            (_now(), chat_id),
        )


def add_waitlist(deal_id: str, mode: str = "WAIT_FOR_GROUP") -> None:
    with db_session() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO waitlist (deal_id, requested_at, mode) VALUES (?, ?, ?)",
            (deal_id, _now(), mode),
        )


def pop_waitlist() -> str | None:
    with db_session() as conn:
        row = conn.execute(
            "SELECT deal_id FROM waitlist ORDER BY requested_at ASC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        deal_id = str(row["deal_id"])
        conn.execute("DELETE FROM waitlist WHERE deal_id = ?", (deal_id,))
        return deal_id
