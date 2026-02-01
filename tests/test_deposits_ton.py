from escrow_bot.services.ton_watch import TonTx, find_matching_deposit


def test_ton_match():
    txs = [
        TonTx(
            tx_hash="aaa",
            to_addr="ADDR",
            memo="DEAL-ABC",
            amount_base_units=100,
            confirmations=3,
            success=True,
        )
    ]
    match = find_matching_deposit(
        txs,
        expected_addr="ADDR",
        expected_memo="DEAL-ABC",
        expected_amount=100,
        confirmations_required=2,
    )
    assert match is not None
    assert match.tx_hash == "aaa"


def test_ton_no_match_on_confirmations():
    txs = [
        TonTx(
            tx_hash="aaa",
            to_addr="ADDR",
            memo="DEAL-ABC",
            amount_base_units=100,
            confirmations=1,
            success=True,
        )
    ]
    match = find_matching_deposit(
        txs,
        expected_addr="ADDR",
        expected_memo="DEAL-ABC",
        expected_amount=100,
        confirmations_required=2,
    )
    assert match is None
