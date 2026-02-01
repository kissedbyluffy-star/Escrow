from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Deal:
    id: str
    buyer_id: int
    seller_id: int
    title: str
    description: str
    deadline: str | None
    proof_types: list[str]
    currency: str
    network: str
    amount: float
    fee_percent: float
    fee_flat: float
    status: str
    immutable: bool
    buyer_confirmed: bool
    seller_confirmed: bool
    created_by: int
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Payment:
    id: str
    deal_id: str
    amount: float
    currency: str
    network: str
    tx_hash: str | None
    status: str
    created_at: str


@dataclass(frozen=True)
class Dispute:
    id: str
    deal_id: str
    opened_by: int
    reason: str
    status: str
    resolution: str | None
    created_at: str
    updated_at: str


def utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"
