from escrow_bot.services.settings import get_setting, set_setting


def test_settings_persistence():
    original = get_setting("fee_percent")
    set_setting("fee_percent", "2")
    assert get_setting("fee_percent") == "2"
    set_setting("fee_percent", original)
