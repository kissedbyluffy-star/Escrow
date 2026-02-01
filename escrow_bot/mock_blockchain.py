from __future__ import annotations

import uuid

from escrow_bot.models import Payment, utc_now
from escrow_bot.repositories import create_payment


class MockBlockchain:
    def __init__(self, conn):
        self.conn = conn

    def simulate_deposit(self, deal_id: str, amount: float, currency: str, network: str, tx_hash: str | None = None) -> Payment:
        payment = Payment(
            id=str(uuid.uuid4()),
            deal_id=deal_id,
            amount=amount,
            currency=currency,
            network=network,
            tx_hash=tx_hash or "mock-tx",
            status="CONFIRMED",
            created_at=utc_now(),
        )
        create_payment(self.conn, payment)
        return payment
