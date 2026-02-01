import pytest

from escrow_bot import db
from escrow_bot.settings_store import get_setting, set_setting, toggle_setting, ensure_defaults


@pytest.fixture()
def conn():
    connection = db.connect(":memory:")
    db.init_db(connection)
    return connection


def test_settings_get_set_toggle(conn):
    ensure_defaults(conn, {"feature_enabled": "false"})
    assert get_setting(conn, "feature_enabled") == "false"

    set_setting(conn, "feature_enabled", "true")
    assert get_setting(conn, "feature_enabled") == "true"

    new_value = toggle_setting(conn, "feature_enabled", False)
    assert new_value is False
    assert get_setting(conn, "feature_enabled") == "false"
