from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: list[int]
    mock_chain: bool
    escrow_addr_ton: str
    escrow_addr_usdt_ton: str
    escrow_addr_usdt_trc20: str
    fee_wallet_ton: str
    fee_wallet_usdt_ton: str
    fee_wallet_usdt_trc20: str
    private_log_channel_id: int | None
    public_log_channel_id: int | None
    updates_channel_url: str | None
    vouches_channel_url: str | None
    support_username_or_url: str | None
    ton_signing_secret: str | None
    tron_private_key: str | None
    callback_hmac_secret: str


def _parse_admin_ids(raw: str) -> list[int]:
    if not raw:
        return []
    return [int(item.strip()) for item in raw.split(",") if item.strip()]


def _optional_int(value: str | None) -> int | None:
    if not value:
        return None
    return int(value)


def load_config() -> Config:
    return Config(
        bot_token=os.getenv("BOT_TOKEN", ""),
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        mock_chain=os.getenv("MOCK_CHAIN", "0") == "1",
        escrow_addr_ton=os.getenv("ESCROW_ADDR_TON", ""),
        escrow_addr_usdt_ton=os.getenv("ESCROW_ADDR_USDT_TON", ""),
        escrow_addr_usdt_trc20=os.getenv("ESCROW_ADDR_USDT_TRC20", ""),
        fee_wallet_ton=os.getenv("FEE_WALLET_TON", ""),
        fee_wallet_usdt_ton=os.getenv("FEE_WALLET_USDT_TON", ""),
        fee_wallet_usdt_trc20=os.getenv("FEE_WALLET_USDT_TRC20", ""),
        private_log_channel_id=_optional_int(os.getenv("PRIVATE_LOG_CHANNEL_ID")),
        public_log_channel_id=_optional_int(os.getenv("PUBLIC_LOG_CHANNEL_ID")),
        updates_channel_url=os.getenv("UPDATES_CHANNEL_URL"),
        vouches_channel_url=os.getenv("VOUCHES_CHANNEL_URL"),
        support_username_or_url=os.getenv("SUPPORT_USERNAME_OR_URL"),
        ton_signing_secret=os.getenv("TON_SIGNING_SECRET"),
        tron_private_key=os.getenv("TRON_PRIVATE_KEY"),
        callback_hmac_secret=os.getenv("CALLBACK_HMAC_SECRET", ""),
    )
