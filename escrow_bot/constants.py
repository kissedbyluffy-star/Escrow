SUPPORTED_CURRENCIES = [
    ("TON", "TON"),
    ("USDT_TON", "USDT on TON"),
    ("USDT_TRC20", "USDT on TRON (TRC20)"),
]

PROOF_TYPES = [
    "Screenshot",
    "Transaction hash",
    "URL/link",
    "File upload",
    "Text confirmation",
]

WARNING_NETWORK = "Sending funds on the wrong network will result in permanent loss."

START_MESSAGE = (
    "Welcome to Escrow Bot.\n\n"
    "We are an escrow facilitator only — not a wallet, exchange, bank, or marketplace.\n"
    "All decisions are subject to admin review and admin-controlled release.\n\n"
    "All interactions are in private chats. No buyer–seller free chat is provided." 
)

DEAL_RULE = "If it is not written in the deal description, it is NOT part of the deal."

IRREVERSIBLE_WARNING = (
    "⚠️ This action is irreversible once confirmed. Please review carefully."
)
