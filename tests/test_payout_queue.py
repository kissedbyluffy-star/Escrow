import json

from escrow_bot.services.deals_service import create_deal
from escrow_bot.services.payouts import enqueue_payout, process_payout_queue
from escrow_bot.services.settings import set_setting


def _deal_id():
    return create_deal(
        {
            "title": "Payout",
            "terms": "deliver item after payment with proof",
            "proof_requirements": json.dumps(["Text Confirm"]),
            "deadline": None,
            "amount_base_units": 1000,
            "display_amount": "1.0",
            "asset": "TON",
            "network": "TON",
            "buyer_tg_id": 1,
            "buyer_username_snapshot": "@buyer",
            "seller_tg_id": 2,
            "seller_username_snapshot": "@seller",
            "status": "READY_TO_PAYOUT",
        }
    )


def test_payout_queue_processing():
    deal_id = _deal_id()
    enqueue_payout(deal_id, "RELEASE", "TON", 900, 100)
    set_setting("PAYOUT_AUTOMATION_ON", "1")
    processed = process_payout_queue(mock_chain=True)
    assert processed == 1
