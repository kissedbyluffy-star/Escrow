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


def _deal(conn):
    buyer = _user(1)
    seller = _user(2)
    return services.create_deal(
        conn,
        buyer,
        buyer_id=buyer.user_id,
        seller_id=seller.user_id,
        title="Content delivery",
        description="I will deliver a report by sending a PDF via a secure link.",
        deadline=None,
        proof_types=["URL/link"],
        currency="USDT",
        network="TON",
        amount=200,
        fee_config=_fees(),
        limits=_limits(),
    )


def test_invalid_transitions(conn):
    buyer = _user(1)
    seller = _user(2)
    deal = _deal(conn)

    with pytest.raises(services.StateError):
        services.mark_funded(conn, buyer, deal.id)

    services.confirm_deal(conn, buyer, deal.id)
    services.confirm_deal(conn, seller, deal.id)

    with pytest.raises(services.StateError):
        services.release_funds(conn, buyer, deal.id)


def test_wrong_user_actions(conn):
    buyer = _user(1)
    seller = _user(2)
    other = _user(3)
    deal = _deal(conn)
    services.confirm_deal(conn, buyer, deal.id)
    services.confirm_deal(conn, seller, deal.id)
    services.mark_funded(conn, buyer, deal.id)

    with pytest.raises(services.PermissionError):
        services.mark_delivered(conn, other, deal.id, proof="proof")
