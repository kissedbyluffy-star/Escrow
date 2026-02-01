import pytest

from escrow_bot import db, services


@pytest.fixture()
def conn():
    connection = db.connect(":memory:")
    db.init_db(connection)
    return connection


def _user(user_id: int):
    return services.UserContext(user_id=user_id, username=f"user{user_id}", is_admin=False)


def _fees():
    return services.FeeConfig(percent=0.0, flat=0.0)


def test_amount_limit(conn):
    buyer = _user(1)
    seller = _user(2)
    limits = services.Limits(max_amount=50, max_active_deals=5, deal_create_rate_limit_seconds=0)

    with pytest.raises(services.ValidationError):
        services.create_deal(
            conn,
            buyer,
            buyer_id=buyer.user_id,
            seller_id=seller.user_id,
            title="Large deal",
            description="I will deliver files by sending a secure link with details included.",
            deadline=None,
            proof_types=["File upload"],
            currency="TON",
            network="TON",
            amount=100,
            fee_config=_fees(),
            limits=limits,
        )


def test_rate_limit(conn):
    buyer = _user(1)
    seller = _user(2)
    limits = services.Limits(max_amount=1000, max_active_deals=5, deal_create_rate_limit_seconds=3600)

    services.create_deal(
        conn,
        buyer,
        buyer_id=buyer.user_id,
        seller_id=seller.user_id,
        title="Deal one",
        description="I will deliver a report by sending a PDF link with instructions.",
        deadline=None,
        proof_types=["URL/link"],
        currency="TON",
        network="TON",
        amount=10,
        fee_config=_fees(),
        limits=limits,
    )

    with pytest.raises(services.ValidationError):
        services.create_deal(
            conn,
            buyer,
            buyer_id=buyer.user_id,
            seller_id=seller.user_id,
            title="Deal two",
            description="I will deliver a report by sending a PDF link with instructions.",
            deadline=None,
            proof_types=["URL/link"],
            currency="TON",
            network="TON",
            amount=10,
            fee_config=_fees(),
            limits=limits,
        )


def test_max_active_deals(conn):
    buyer = _user(1)
    seller = _user(2)
    limits = services.Limits(max_amount=1000, max_active_deals=1, deal_create_rate_limit_seconds=0)

    services.create_deal(
        conn,
        buyer,
        buyer_id=buyer.user_id,
        seller_id=seller.user_id,
        title="Deal one",
        description="I will deliver a report by sending a PDF link with instructions.",
        deadline=None,
        proof_types=["URL/link"],
        currency="TON",
        network="TON",
        amount=10,
        fee_config=_fees(),
        limits=limits,
    )

    with pytest.raises(services.ValidationError):
        services.create_deal(
            conn,
            buyer,
            buyer_id=buyer.user_id,
            seller_id=seller.user_id,
            title="Deal two",
            description="I will deliver a report by sending a PDF link with instructions.",
            deadline=None,
            proof_types=["URL/link"],
            currency="TON",
            network="TON",
            amount=10,
            fee_config=_fees(),
            limits=limits,
        )
