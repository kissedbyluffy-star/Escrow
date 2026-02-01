from escrow_bot.deposit_service import format_ton_memo, ton_memo_matches


def test_format_ton_memo():
    assert format_ton_memo("abc") == "DEAL-abc"


def test_ton_memo_matches():
    assert ton_memo_matches("DEAL-123", "DEAL-123") is True
    assert ton_memo_matches("deal-123", "DEAL-123") is False
