from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from escrow_bot import repositories
from escrow_bot.models import Deal, Dispute, Payment, utc_now

ALLOWED_STATUSES = {
    "DRAFT",
    "CONFIRMED",
    "FUNDED",
    "DELIVERED",
    "RELEASED",
    "DISPUTED",
    "CLOSED",
}


class EscrowError(Exception):
    pass


class PermissionError(EscrowError):
    pass


class ValidationError(EscrowError):
    pass


class StateError(EscrowError):
    pass


@dataclass(frozen=True)
class FeeConfig:
    percent: float
    flat: float


@dataclass(frozen=True)
class Limits:
    max_amount: float
    max_active_deals: int
    deal_create_rate_limit_seconds: int


@dataclass(frozen=True)
class UserContext:
    user_id: int
    username: str | None
    is_admin: bool


def create_deal(
    conn,
    user: UserContext,
    buyer_id: int,
    seller_id: int,
    title: str,
    description: str,
    deadline: str | None,
    proof_types: list[str],
    currency: str,
    network: str,
    amount: float,
    fee_config: FeeConfig,
    limits: Limits,
) -> Deal:
    _enforce_limits(conn, user.user_id, amount, limits)
    _validate_title(title)
    _validate_description(description)
    _validate_proof_types(proof_types)
    _validate_currency(currency, network)

    deal_id = str(uuid.uuid4())
    now = utc_now()
    deal = Deal(
        id=deal_id,
        buyer_id=buyer_id,
        seller_id=seller_id,
        title=title.strip(),
        description=description.strip(),
        deadline=deadline,
        proof_types=proof_types,
        currency=currency,
        network=network,
        amount=amount,
        fee_percent=fee_config.percent,
        fee_flat=fee_config.flat,
        status="DRAFT",
        immutable=False,
        buyer_confirmed=user.user_id == buyer_id,
        seller_confirmed=user.user_id == seller_id,
        created_by=user.user_id,
        created_at=now,
        updated_at=now,
    )
    repositories.create_deal(conn, deal)
    repositories.log_audit(conn, str(uuid.uuid4()), user.user_id, "deal_created", deal_id, "{}", now)
    return deal


def confirm_deal(conn, user: UserContext, deal_id: str) -> Deal:
    deal = _get_deal_or_raise(conn, deal_id)
    if deal.status != "DRAFT":
        raise StateError("Deal is not in draft state.")
    if user.user_id not in {deal.buyer_id, deal.seller_id}:
        raise PermissionError("Only parties can confirm this deal.")
    now = utc_now()
    fields = {"updated_at": now}
    if user.user_id == deal.buyer_id:
        fields["buyer_confirmed"] = 1
    if user.user_id == deal.seller_id:
        fields["seller_confirmed"] = 1
    repositories.update_deal(conn, deal_id, fields)
    updated = _get_deal_or_raise(conn, deal_id)
    if updated.buyer_confirmed and updated.seller_confirmed:
        repositories.update_deal(
            conn,
            deal_id,
            {"status": "CONFIRMED", "immutable": 1, "updated_at": now},
        )
    repositories.log_audit(conn, str(uuid.uuid4()), user.user_id, "deal_confirmed", deal_id, "{}", now)
    return _get_deal_or_raise(conn, deal_id)


def mark_funded(conn, user: UserContext, deal_id: str, tx_hash: str | None = None) -> Payment:
    deal = _get_deal_or_raise(conn, deal_id)
    if deal.status != "CONFIRMED":
        raise StateError("Deal must be confirmed before funding.")
    if user.user_id != deal.buyer_id and not user.is_admin:
        raise PermissionError("Only buyer or admin can mark funded.")
    payment = Payment(
        id=str(uuid.uuid4()),
        deal_id=deal_id,
        amount=deal.amount,
        currency=deal.currency,
        network=deal.network,
        tx_hash=tx_hash,
        status="CONFIRMED",
        created_at=utc_now(),
    )
    repositories.create_payment(conn, payment)
    repositories.update_deal(conn, deal_id, {"status": "FUNDED", "updated_at": payment.created_at})
    repositories.log_audit(
        conn,
        str(uuid.uuid4()),
        user.user_id,
        "deal_funded",
        deal_id,
        json.dumps({"tx_hash": tx_hash or "mock"}),
        payment.created_at,
    )
    return payment


def mark_delivered(conn, user: UserContext, deal_id: str, proof: str) -> Deal:
    deal = _get_deal_or_raise(conn, deal_id)
    if deal.status != "FUNDED":
        raise StateError("Deal must be funded before delivery.")
    if user.user_id != deal.seller_id:
        raise PermissionError("Only seller can mark delivered.")
    now = utc_now()
    repositories.update_deal(conn, deal_id, {"status": "DELIVERED", "updated_at": now})
    repositories.log_audit(
        conn,
        str(uuid.uuid4()),
        user.user_id,
        "deal_delivered",
        deal_id,
        json.dumps({"proof": proof}),
        now,
    )
    return _get_deal_or_raise(conn, deal_id)


def release_funds(conn, user: UserContext, deal_id: str) -> Deal:
    deal = _get_deal_or_raise(conn, deal_id)
    if deal.status != "DELIVERED":
        raise StateError("Deal must be delivered before release.")
    if user.user_id != deal.buyer_id and not user.is_admin:
        raise PermissionError("Only buyer or admin can release funds.")
    now = utc_now()
    repositories.update_deal(conn, deal_id, {"status": "RELEASED", "updated_at": now})
    repositories.log_audit(conn, str(uuid.uuid4()), user.user_id, "deal_released", deal_id, "{}", now)
    return _get_deal_or_raise(conn, deal_id)


def open_dispute(conn, user: UserContext, deal_id: str, reason: str) -> Dispute:
    deal = _get_deal_or_raise(conn, deal_id)
    if deal.status not in {"DELIVERED", "FUNDED"}:
        raise StateError("Dispute can only be opened after funding or delivery.")
    if user.user_id not in {deal.buyer_id, deal.seller_id}:
        raise PermissionError("Only parties can dispute.")
    now = utc_now()
    dispute = Dispute(
        id=str(uuid.uuid4()),
        deal_id=deal_id,
        opened_by=user.user_id,
        reason=reason.strip(),
        status="OPEN",
        resolution=None,
        created_at=now,
        updated_at=now,
    )
    repositories.create_dispute(conn, dispute)
    repositories.update_deal(conn, deal_id, {"status": "DISPUTED", "updated_at": now})
    repositories.log_audit(conn, str(uuid.uuid4()), user.user_id, "dispute_opened", deal_id, "{}", now)
    return dispute


def resolve_dispute(conn, user: UserContext, deal_id: str, resolution: str, close_status: str) -> Deal:
    if not user.is_admin:
        raise PermissionError("Admin only action.")
    deal = _get_deal_or_raise(conn, deal_id)
    dispute = repositories.get_dispute_for_deal(conn, deal_id)
    if not dispute:
        raise StateError("No dispute found for deal.")
    now = utc_now()
    repositories.update_dispute(
        conn,
        dispute.id,
        {"status": "RESOLVED", "resolution": resolution, "updated_at": now},
    )
    repositories.update_deal(conn, deal_id, {"status": close_status, "updated_at": now})
    repositories.log_audit(
        conn,
        str(uuid.uuid4()),
        user.user_id,
        "dispute_resolved",
        deal_id,
        json.dumps({"resolution": resolution, "status": close_status}),
        now,
    )
    return _get_deal_or_raise(conn, deal_id)


def close_deal(conn, user: UserContext, deal_id: str) -> Deal:
    if not user.is_admin:
        raise PermissionError("Admin only action.")
    deal = _get_deal_or_raise(conn, deal_id)
    now = utc_now()
    repositories.update_deal(conn, deal_id, {"status": "CLOSED", "updated_at": now})
    repositories.log_audit(conn, str(uuid.uuid4()), user.user_id, "deal_closed", deal_id, "{}", now)
    return _get_deal_or_raise(conn, deal_id)


def calculate_fee(amount: float, fee_config: FeeConfig) -> float:
    return round(amount * (fee_config.percent / 100.0) + fee_config.flat, 8)


def _enforce_limits(conn, user_id: int, amount: float, limits: Limits) -> None:
    if amount > limits.max_amount:
        raise ValidationError("Amount exceeds configured maximum.")
    active_deals = repositories.list_user_active_deals(conn, user_id)
    if len(active_deals) >= limits.max_active_deals:
        raise ValidationError("You have reached the maximum number of active deals.")
    threshold = datetime.utcnow() - timedelta(seconds=limits.deal_create_rate_limit_seconds)
    recent_deals = repositories.list_deals_created_after(conn, user_id, threshold.isoformat(timespec="seconds") + "Z")
    if recent_deals:
        raise ValidationError("Deal creation rate limit reached. Please wait before creating another deal.")


def _validate_title(title: str) -> None:
    if not title or len(title.strip()) < 5:
        raise ValidationError("Title must be at least 5 characters.")


def _validate_description(description: str) -> None:
    if not description or len(description.strip()) < 40:
        raise ValidationError("Description is too short. Please provide full delivery details.")
    keywords = {"deliver", "delivery", "provide", "send", "ship", "handover"}
    if not any(word in description.lower() for word in keywords):
        raise ValidationError("Description must explain delivery details explicitly.")


def _validate_proof_types(proof_types: list[str]) -> None:
    if not proof_types:
        raise ValidationError("At least one proof type is required.")


def _validate_currency(currency: str, network: str) -> None:
    valid = {
        ("TON", "TON"),
        ("USDT", "TON"),
        ("USDT", "TRON"),
    }
    if (currency, network) not in valid:
        raise ValidationError("Unsupported currency/network combination.")


def _get_deal_or_raise(conn, deal_id: str) -> Deal:
    deal = repositories.get_deal(conn, deal_id)
    if not deal:
        raise ValidationError("Deal not found.")
    if deal.status not in ALLOWED_STATUSES:
        raise StateError("Invalid deal state.")
    return deal
