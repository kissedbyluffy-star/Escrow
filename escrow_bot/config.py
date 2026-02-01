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
    mock_blockchain: bool
    log_level: str
    fee_percent: float
    fee_flat: float
    max_deal_amount: float
    max_active_deals_per_user: int
    deal_create_rate_limit_seconds: int
    ton_deposit_address: str
    usdt_ton_deposit_address: str
    usdt_tron_deposit_address: str
    fee_wallet_ton: str
    fee_wallet_usdt_ton: str
    fee_wallet_usdt_trc20: str
    updates_channel_url: str
    vouches_channel_url: str
    support_username_or_url: str
    private_log_channel_id: str
    public_log_channel_id: str
    confirmations_required_ton: int
    confirmations_required_tron: int
    ton_api_url: str
    ton_api_key: str
    tron_api_url: str


def load_settings() -> Settings:
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", ""),
        admin_ids=_split_ints(os.getenv("ADMIN_IDS", "")),
        database_path=os.getenv("DATABASE_PATH", "escrow.db"),
        mock_blockchain=os.getenv("MOCK_BLOCKCHAIN", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        fee_percent=float(os.getenv("FEE_PERCENT", "1")),
        fee_flat=float(os.getenv("FEE_FLAT", "0")),
        max_deal_amount=float(os.getenv("MAX_DEAL_AMOUNT", "10000")),
        max_active_deals_per_user=int(os.getenv("MAX_ACTIVE_DEALS_PER_USER", "5")),
        deal_create_rate_limit_seconds=int(os.getenv("DEAL_CREATE_RATE_LIMIT_SECONDS", "60")),
        ton_deposit_address=os.getenv("TON_DEPOSIT_ADDRESS", ""),
        usdt_ton_deposit_address=os.getenv("USDT_TON_DEPOSIT_ADDRESS", ""),
        usdt_tron_deposit_address=os.getenv("USDT_TRC20_DEPOSIT_ADDRESS", ""),
        fee_wallet_ton=os.getenv("FEE_WALLET_TON", ""),
        fee_wallet_usdt_ton=os.getenv("FEE_WALLET_USDT_TON", ""),
        fee_wallet_usdt_trc20=os.getenv("FEE_WALLET_USDT_TRC20", ""),
        updates_channel_url=os.getenv("UPDATES_CHANNEL_URL", ""),
        vouches_channel_url=os.getenv("VOUCHES_CHANNEL_URL", ""),
        support_username_or_url=os.getenv("SUPPORT_USERNAME_OR_URL", ""),
        private_log_channel_id=os.getenv("PRIVATE_LOG_CHANNEL_ID", ""),
        public_log_channel_id=os.getenv("PUBLIC_LOG_CHANNEL_ID", ""),
        confirmations_required_ton=int(os.getenv("CONFIRMATIONS_REQUIRED_TON", "3")),
        confirmations_required_tron=int(os.getenv("CONFIRMATIONS_REQUIRED_TRON", "20")),
        ton_api_url=os.getenv("TON_API_URL", "https://toncenter.com/api/v2/getTransactions"),
        ton_api_key=os.getenv("TON_API_KEY", ""),
        tron_api_url=os.getenv("TRON_API_URL", "https://apilist.tronscan.org/api/transaction-info"),
    )
