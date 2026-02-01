from __future__ import annotations

import logging
from datetime import datetime

from escrow_bot import ui_text
from escrow_bot.settings_store import get_bool, get_setting

logger = logging.getLogger(__name__)


def mask_username(username: str | None, mode: str = "masked") -> str:
    if not username:
        return "@user"
    handle = username.lstrip("@")
    if len(handle) <= 2:
        return f"@{handle}"
    if mode == "extra":
        return f"@{handle[0]}***"
    return f"@{handle[:2]}***{handle[-2:]}"


def mask_tx(tx_hash: str | None, mode: str = "masked") -> str:
    if not tx_hash:
        return ""
    if mode == "extra":
        return f"{tx_hash[:4]}..."
    return f"{tx_hash[:4]}...{tx_hash[-4:]}"


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")


def render_private_log(event: str, deal: dict, meta: dict) -> str:
    tx_hash = meta.get("tx_hash")
    return (
        f"<b>🔒 Escrow Log</b>\n"
        f"<b>Event:</b> {event}\n"
        f"<b>Deal:</b> <code>{deal['id']}</code>\n"
        f"<b>Status:</b> {ui_text.status_emoji(deal['status'])} {ui_text.status_text(deal['status'])}\n"
        f"<b>Amount:</b> {deal['amount']} {deal['currency']} ({deal['network']})\n"
        f"<b>Buyer:</b> @{meta.get('buyer', 'unknown')}\n"
        f"<b>Seller:</b> @{meta.get('seller', 'unknown')}\n"
        f"<b>Tx:</b> {tx_hash or '—'}\n"
        f"<b>Time:</b> {_timestamp()}"
    )


def render_public_log(event: str, deal: dict, meta: dict, masking_mode: str) -> str:
    completed = "Completed ✅" if event == "Released" else ""
    return (
        f"{ui_text.status_emoji(deal['status'])} <b>{deal['title']}</b>\n"
        f"• {deal['amount']} {deal['currency']}\n"
        f"• Network: {deal['network']}\n"
        f"• {_timestamp()}\n"
        f"{completed}"
    ).strip()


def should_log_event(conn, event_key: str) -> bool:
    return get_bool(conn, f"log_event_{event_key}", True)


def log_event(bot, conn, admin_ids: list[int], event: str, event_key: str, deal: dict, meta: dict) -> None:
    if not should_log_event(conn, event_key):
        return
    private_enabled = get_bool(conn, "logs_private_enabled", False)
    public_enabled = get_bool(conn, "logs_public_enabled", False)
    masking_mode = get_setting(conn, "public_masking_mode", "masked")
    private_channel = get_setting(conn, "private_log_channel_id")
    public_channel = get_setting(conn, "public_log_channel_id")

    try:
        if private_enabled and private_channel:
            bot.send_message(
                chat_id=int(private_channel),
                text=render_private_log(event, deal, meta),
                parse_mode="HTML",
            )
        if public_enabled and public_channel:
            bot.send_message(
                chat_id=int(public_channel),
                text=render_public_log(event, deal, meta, masking_mode),
                parse_mode="HTML",
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Log dispatch failed: %s", exc)
        for admin_id in admin_ids:
            try:
                bot.send_message(
                    chat_id=admin_id,
                    text="⚠️ Log dispatch failed. Check channel settings/permissions.",
                    parse_mode="HTML",
                )
            except Exception:
                logger.exception("Failed to notify admin about logging failure")
