from __future__ import annotations

import sqlite3
from typing import Any

from escrow_bot import db
from escrow_bot.models import Deal, Dispute, Payment


def upsert_user(conn: sqlite3.Connection, user_id: int, username: str | None, created_at: str) -> None:
    db.execute(
        conn,
        """
        INSERT INTO users (id, username, created_at)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET username=excluded.username
        """,
        (user_id, username, created_at),
    )


def create_deal(conn: sqlite3.Connection, deal: Deal) -> None:
    db.execute(
        conn,
        """
        INSERT INTO deals (
            id, buyer_id, seller_id, title, description, deadline, proof_types, currency, network, amount,
            fee_percent, fee_flat, status, immutable, buyer_confirmed, seller_confirmed, created_by, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            deal.id,
            deal.buyer_id,
            deal.seller_id,
            deal.title,
            deal.description,
            deal.deadline,
            db.json_dump(deal.proof_types),
            deal.currency,
            deal.network,
            deal.amount,
            deal.fee_percent,
            deal.fee_flat,
            deal.status,
            int(deal.immutable),
            int(deal.buyer_confirmed),
            int(deal.seller_confirmed),
            deal.created_by,
            deal.created_at,
            deal.updated_at,
        ),
    )


def update_deal(conn: sqlite3.Connection, deal_id: str, fields: dict[str, Any]) -> None:
    if not fields:
        return
    columns = ", ".join(f"{key}=?" for key in fields)
    params = list(fields.values()) + [deal_id]
    db.execute(conn, f"UPDATE deals SET {columns} WHERE id=?", params)


def get_deal(conn: sqlite3.Connection, deal_id: str) -> Deal | None:
    row = db.fetch_one(conn, "SELECT * FROM deals WHERE id=?", (deal_id,))
    if not row:
        return None
    return _deal_from_row(row)


def list_user_active_deals(conn: sqlite3.Connection, user_id: int) -> list[Deal]:
    rows = db.fetch_all(
        conn,
        """
        SELECT * FROM deals
        WHERE (buyer_id=? OR seller_id=?) AND status IN ('DRAFT','CONFIRMED','FUNDED','DELIVERED','DISPUTED')
        """,
        (user_id, user_id),
    )
    return [_deal_from_row(row) for row in rows]


def list_user_deals(conn: sqlite3.Connection, user_id: int, limit: int = 10) -> list[Deal]:
    rows = db.fetch_all(
        conn,
        """
        SELECT * FROM deals
        WHERE buyer_id=? OR seller_id=?
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (user_id, user_id, limit),
    )
    return [_deal_from_row(row) for row in rows]


def list_deals_created_after(conn: sqlite3.Connection, user_id: int, timestamp: str) -> list[Deal]:
    rows = db.fetch_all(
        conn,
        "SELECT * FROM deals WHERE created_by=? AND created_at >= ?",
        (user_id, timestamp),
    )
    return [_deal_from_row(row) for row in rows]


def list_confirmed_deals_for_network(conn: sqlite3.Connection, currency: str, network: str) -> list[Deal]:
    rows = db.fetch_all(
        conn,
        "SELECT * FROM deals WHERE status='CONFIRMED' AND currency=? AND network=?",
        (currency, network),
    )
    return [_deal_from_row(row) for row in rows]


def create_payment(conn: sqlite3.Connection, payment: Payment) -> None:
    db.execute(
        conn,
        """
        INSERT INTO payments (id, deal_id, amount, currency, network, tx_hash, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payment.id,
            payment.deal_id,
            payment.amount,
            payment.currency,
            payment.network,
            payment.tx_hash,
            payment.status,
            payment.created_at,
        ),
    )


def list_payments_for_deal(conn: sqlite3.Connection, deal_id: str) -> list[Payment]:
    rows = db.fetch_all(conn, "SELECT * FROM payments WHERE deal_id=?", (deal_id,))
    return [_payment_from_row(row) for row in rows]


def create_dispute(conn: sqlite3.Connection, dispute: Dispute) -> None:
    db.execute(
        conn,
        """
        INSERT INTO disputes (id, deal_id, opened_by, reason, status, resolution, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            dispute.id,
            dispute.deal_id,
            dispute.opened_by,
            dispute.reason,
            dispute.status,
            dispute.resolution,
            dispute.created_at,
            dispute.updated_at,
        ),
    )


def update_dispute(conn: sqlite3.Connection, dispute_id: str, fields: dict[str, Any]) -> None:
    if not fields:
        return
    columns = ", ".join(f"{key}=?" for key in fields)
    params = list(fields.values()) + [dispute_id]
    db.execute(conn, f"UPDATE disputes SET {columns} WHERE id=?", params)


def get_dispute_for_deal(conn: sqlite3.Connection, deal_id: str) -> Dispute | None:
    row = db.fetch_one(conn, "SELECT * FROM disputes WHERE deal_id=?", (deal_id,))
    if not row:
        return None
    return _dispute_from_row(row)


def log_audit(conn: sqlite3.Connection, audit_id: str, actor_id: int, action: str, deal_id: str | None, metadata: str, created_at: str) -> None:
    db.execute(
        conn,
        """
        INSERT INTO audit_logs (id, actor_id, action, deal_id, metadata, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (audit_id, actor_id, action, deal_id, metadata, created_at),
    )


def get_username(conn: sqlite3.Connection, user_id: int) -> str | None:
    row = db.fetch_one(conn, "SELECT username FROM users WHERE id=?", (user_id,))
    return row["username"] if row else None


def _deal_from_row(row: sqlite3.Row) -> Deal:
    return Deal(
        id=row["id"],
        buyer_id=row["buyer_id"],
        seller_id=row["seller_id"],
        title=row["title"],
        description=row["description"],
        deadline=row["deadline"],
        proof_types=db.json_load(row["proof_types"]),
        currency=row["currency"],
        network=row["network"],
        amount=row["amount"],
        fee_percent=row["fee_percent"],
        fee_flat=row["fee_flat"],
        status=row["status"],
        immutable=bool(row["immutable"]),
        buyer_confirmed=bool(row["buyer_confirmed"]),
        seller_confirmed=bool(row["seller_confirmed"]),
        created_by=row["created_by"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _payment_from_row(row: sqlite3.Row) -> Payment:
    return Payment(
        id=row["id"],
        deal_id=row["deal_id"],
        amount=row["amount"],
        currency=row["currency"],
        network=row["network"],
        tx_hash=row["tx_hash"],
        status=row["status"],
        created_at=row["created_at"],
    )


def _dispute_from_row(row: sqlite3.Row) -> Dispute:
    return Dispute(
        id=row["id"],
        deal_id=row["deal_id"],
        opened_by=row["opened_by"],
        reason=row["reason"],
        status=row["status"],
        resolution=row["resolution"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
