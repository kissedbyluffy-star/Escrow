import pytest

from escrow_bot import db, services


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
    return services.FeeConfig(percent=0.0, flat=0.0)


def _confirmed_deal(conn):
    buyer = _user(1)
    seller = _user(2)
    deal = services.create_deal(
        conn,
        buyer,
        buyer_id=buyer.user_id,
        seller_id=seller.user_id,
        title="Graphic delivery",
        description="I will deliver design files by sending a download link.",
        deadline=None,
        proof_types=["File upload"],
        currency="USDT",
        network="TRON",
        amount=300,
        fee_config=_fees(),
        limits=_limits(),
    )
    services.confirm_deal(conn, buyer, deal.id)
    services.confirm_deal(conn, seller, deal.id)
    return deal


def test_admin_resolve_dispute(conn):
    buyer = _user(1)
    seller = _user(2)
    admin = _user(99, is_admin=True)
    deal = _confirmed_deal(conn)

    services.mark_funded(conn, buyer, deal.id)
    services.mark_delivered(conn, seller, deal.id, proof="link")
    services.open_dispute(conn, buyer, deal.id, reason="Issue")

    resolved = services.resolve_dispute(conn, admin, deal.id, "Refund", "CLOSED")
    assert resolved.status == "CLOSED"


def test_admin_only_actions(conn):
    buyer = _user(1)
    deal = _confirmed_deal(conn)

    with pytest.raises(services.PermissionError):
        services.close_deal(conn, buyer, deal.id)
