import json

from escrow_bot.services.deals_service import create_deal, get_deal, update_deal_status


def test_deal_lifecycle():
    deal_id = create_deal(
        {
            "title": "Test Deal",
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
    update_deal_status(deal_id, "CONFIRMED")
    update_deal_status(deal_id, "FUNDED")
    update_deal_status(deal_id, "DELIVERED")
    update_deal_status(deal_id, "READY_TO_PAYOUT")
    update_deal_status(deal_id, "RELEASED")
    update_deal_status(deal_id, "CLOSED")
    deal = get_deal(deal_id)
    assert deal["status"] == "CLOSED"
