import json
import sqlite3

import pytest

from escrow_bot.services.deals_service import add_deposit, create_deal


def _deal_id():
    return create_deal(
        {
            "title": "Deal",
            "terms": "deliver item after payment with proof",
            "proof_requirements": json.dumps(["Screenshot"]),
            "deadline": None,
            "amount_base_units": 1000,
            "display_amount": "1.0",
            "asset": "TON",
            "network": "TON",
            "buyer_tg_id": 1,
            "buyer_username_snapshot": "@buyer",
            "seller_tg_id": 2,
            "seller_username_snapshot": "@seller",
            "status": "DRAFT",
        }
    )


def test_tx_hash_unique():
    deal_id = _deal_id()
    add_deposit(deal_id, "abcd1234abcd1234", "ADDR", 100, 3)
    with pytest.raises(sqlite3.IntegrityError):
        add_deposit(deal_id, "abcd1234abcd1234", "ADDR", 100, 3)
