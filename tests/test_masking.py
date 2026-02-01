from escrow_bot.logging_service import mask_username, mask_tx


def test_mask_username_default():
    assert mask_username("alice123") == "@al***23"
    assert mask_username("ab") == "@ab"


def test_mask_username_extra():
    assert mask_username("alice123", mode="extra") == "@a***"


def test_mask_tx():
    assert mask_tx("9a3f1234b21c") == "9a3f...b21c"
    assert mask_tx("9a3f1234b21c", mode="extra") == "9a3f..."
