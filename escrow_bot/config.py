import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _split_ints(value: str) -> list[int]:
    if not value:
        return []
    return [int(item.strip()) for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: list[int]
    database_path: str
    fee_percent: float
    fee_flat: float
    max_deal_amount: float
    max_active_deals_per_user: int
    deal_create_rate_limit_seconds: int
    mock_blockchain: bool
    log_level: str
    ton_deposit_address: str
    usdt_ton_deposit_address: str
    usdt_tron_deposit_address: str


def load_settings() -> Settings:
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", ""),
        admin_ids=_split_ints(os.getenv("ADMIN_IDS", "")),
        database_path=os.getenv("DATABASE_PATH", "escrow.db"),
        fee_percent=float(os.getenv("FEE_PERCENT", "0")),
        fee_flat=float(os.getenv("FEE_FLAT", "0")),
        max_deal_amount=float(os.getenv("MAX_DEAL_AMOUNT", "10000")),
        max_active_deals_per_user=int(os.getenv("MAX_ACTIVE_DEALS_PER_USER", "5")),
        deal_create_rate_limit_seconds=int(os.getenv("DEAL_CREATE_RATE_LIMIT_SECONDS", "60")),
        mock_blockchain=os.getenv("MOCK_BLOCKCHAIN", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        ton_deposit_address=os.getenv("TON_DEPOSIT_ADDRESS", ""),
        usdt_ton_deposit_address=os.getenv("USDT_TON_DEPOSIT_ADDRESS", ""),
        usdt_tron_deposit_address=os.getenv("USDT_TRC20_DEPOSIT_ADDRESS", ""),
    )
