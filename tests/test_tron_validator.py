from escrow_bot.deposit_service import DepositExpectation, tron_usdt_matches


def test_tron_usdt_matches():
    expectation = DepositExpectation(
        address="TDEST",
        amount=12.5,
        memo=None,
        confirmations_required=20,
        currency="USDT",
        network="TRON",
    )
    tx = {
        "contract_type": "TRC20",
        "token_info": {"symbol": "USDT"},
        "to_address": "TDEST",
        "amount": 12.5 * 1_000_000,
        "confirmations": 25,
    }
    valid, error = tron_usdt_matches(tx, expectation)
    assert valid is True
    assert error == ""


def test_tron_usdt_mismatch_amount():
    expectation = DepositExpectation(
        address="TDEST",
        amount=12.5,
        memo=None,
        confirmations_required=1,
        currency="USDT",
        network="TRON",
    )
    tx = {
        "contract_type": "TRC20",
        "token_info": {"symbol": "USDT"},
        "to_address": "TDEST",
        "amount": 11 * 1_000_000,
        "confirmations": 3,
    }
    valid, error = tron_usdt_matches(tx, expectation)
    assert valid is False
    assert "Amount" in error
