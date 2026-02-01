from escrow_bot.utils.masking import mask_text


def test_masking_modes():
    text = "@abraham tx 9a3f12bcd1112222"
    masked = mask_text(text, mode="masked")
    assert "@ab***am" in masked
    assert "9a3f...2222" in masked
    extra = mask_text(text, mode="extra-masked")
    assert "@a***" in extra
    assert "9a3f..." in extra
