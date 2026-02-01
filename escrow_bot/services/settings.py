from __future__ import annotations

from datetime import datetime, timezone

from escrow_bot.services.db import db_session

DEFAULT_SETTINGS = {
    "fee_percent": "1",
    "fee_flat": "0",
    "confirmations_required_ton": "3",
    "confirmations_required_tron": "20",
    "AUTO_PAYOUT_MAX": "1000000000",
    "DAILY_PAYOUT_CAP": "5000000000",
    "HOURLY_PAYOUT_CAP": "1000000000",
    "MAX_PAYOUTS_PER_MINUTE": "3",
    "max_deal_amount": "1000000000",
    "max_active_deals_per_user": "5",
    "PRIVATE_LOGS_ON": "1",
    "PUBLIC_LOGS_ON": "0",
    "PUBLIC_MASK_MODE": "masked",
    "PAYOUT_AUTOMATION_ON": "0",
    "PAUSE_PAYOUTS": "0",
    "ERROR_AUTO_PAUSE": "1",
    "ANTI_SPAM_MODE": "0",
    "GROUP_MODE": "OFF",
    "GROUP_LOCK_BEFORE_FUNDED": "1",
    "terms_version": "1.0",
    "REQUIRE_TERMS_REACCEPT_ON_UPDATE": "1",
    "RL_START_PER_MIN": "6",
    "RL_CALLBACKS_PER_MIN": "25",
    "RL_NEWDEAL_COOLDOWN_SEC": "90",
    "RL_CONFIRM_PER_MIN": "8",
    "RL_TX_VERIFY_PER_HOUR": "5",
    "RL_INVALID_TX_PER_HOUR": "3",
    "INVALID_TX_COOLDOWN_MIN": "30",
    "RL_PROOF_UPLOAD_PER_HOUR": "10",
    "GLOBAL_RPS_SOFT_LIMIT": "25",
    "GLOBAL_RPS_HARD_LIMIT": "60",
    "GLOBAL_RPS_HARD_WINDOW_SEC": "10",
    "AUTO_ENABLE_ANTI_SPAM_MINUTES": "15",
    "CAPTCHA_REQUIRED_FOR_NEW_USERS_HOURS": "24",
    "CAPTCHA_FAIL_LIMIT": "3",
    "CAPTCHA_LOCK_MINUTES": "10",
    "MIN_DAYS_SINCE_FIRST_SEEN_FOR_AUTO_PAYOUT": "7",
    "AUTO_BLOCK_THRESHOLD": "100",
}


def seed_defaults() -> None:
    with db_session() as conn:
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )


def get_setting(key: str) -> str:
    with db_session() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        raise KeyError(f"Missing setting: {key}")
    return str(row["value"])


def set_setting(key: str, value: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with db_session() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('updated_at', ?)",
            (now,),
        )
