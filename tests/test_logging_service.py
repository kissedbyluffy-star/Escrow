import pytest

from escrow_bot import db
from escrow_bot.logging_service import log_event
from escrow_bot.settings_store import set_setting


class FakeBot:
    def __init__(self):
        self.messages = []

    def send_message(self, chat_id, text, parse_mode=None):
        self.messages.append({"chat_id": chat_id, "text": text, "parse_mode": parse_mode})


@pytest.fixture()
def conn():
    connection = db.connect(":memory:")
    db.init_db(connection)
    return connection


def test_logging_service_private_public(conn):
    set_setting(conn, "logs_private_enabled", "true")
    set_setting(conn, "logs_public_enabled", "true")
    set_setting(conn, "private_log_channel_id", "-1001")
    set_setting(conn, "public_log_channel_id", "-1002")
    set_setting(conn, "log_event_deal_created", "true")

    bot = FakeBot()
    deal = {"id": "abc", "status": "CONFIRMED", "amount": 10, "currency": "TON", "network": "TON", "title": "Test"}
    log_event(bot, conn, [1], "Deal Created", "deal_created", deal, {"buyer": "buyer", "seller": "seller"})

    assert len(bot.messages) == 2
    assert bot.messages[0]["chat_id"] == -1001
    assert bot.messages[1]["chat_id"] == -1002
