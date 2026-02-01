import pytest

from escrow_bot import db, services
from escrow_bot.models import utc_now


@pytest.fixture()
def conn():
    connection = db.connect(":memory:")
    db.init_db(connection)
    return connection


def _user(user_id: int, is_admin: bool = False):
    return services.UserContext(user_id=user_id, username=f"user{user_id}", is_admin=is_admin)


def _limits():
    return services.Limits(max_amount=1000, max_active_deals=5, deal_create_rate_limit_seconds=0)


def _fees():
    return services.FeeConfig(percent=1.0, flat=0.5)


def test_deal_lifecycle(conn):
    buyer = _user(1)
    seller = _user(2)
    deal = services.create_deal(
        conn,
        buyer,
        buyer_id=buyer.user_id,
        seller_id=seller.user_id,
        title="Website delivery",
        description="I will deliver a website by sending a zip file and deployment notes.",
        deadline=utc_now(),
        proof_types=["URL/link"],
        currency="TON",
        network="TON",
        amount=100,
        fee_config=_fees(),
        limits=_limits(),
    )
    assert deal.status == "DRAFT"

    deal = services.confirm_deal(conn, buyer, deal.id)
    assert deal.status == "DRAFT"
    deal = services.confirm_deal(conn, seller, deal.id)
    assert deal.status == "CONFIRMED"

    payment = services.mark_funded(conn, buyer, deal.id, tx_hash="0xabc")
    assert payment.status == "CONFIRMED"

    deal = services.mark_delivered(conn, seller, deal.id, proof="https://example.com")
    assert deal.status == "DELIVERED"

    deal = services.release_funds(conn, buyer, deal.id)
    assert deal.status == "RELEASED"
