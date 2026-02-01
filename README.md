# Escrow Telegram Bot

A **safe, minimal, production-ready escrow facilitator bot** built on `python-telegram-bot` v21 (async). It is **not** a wallet, exchange, bank, or marketplace. All interactions are in private bot chats, and **admin-controlled fund release** is mandatory.

## What this bot does
- Facilitates escrow deals between a buyer and seller.
- Records immutable deal terms and proof requirements.
- Tracks escrow state transitions with audit logs.
- Supports admin-only dispute resolution and fund release.

## What this bot does NOT do
- ❌ Hold private keys or provide custody services.
- ❌ Run a P2P marketplace or enable buyer–seller free chat.
- ❌ Perform automatic withdrawals or payouts.
- ❌ Handle fiat currencies.

## Supported currencies (locked)
- TON (native)
- USDT on TON network
- USDT on TRON network (TRC20)

**Warning:** Sending funds on the wrong network will result in permanent loss.

## Escrow flow
1. `/start` → rules and overview.
2. `/newdeal` wizard:
   - Role selection
   - Counterparty @username
   - Deal title
   - Detailed description (vague input rejected)
   - Proof type selection
   - Currency & network
   - Amount
   - Full summary + fee + risk warnings
   - Deal creation (creator confirms immediately)
3. Counterparty confirms via `/confirmdeal <deal_id>`.
4. Buyer uses `/deposit <deal_id>` for deposit instructions.
5. Deposit detected and recorded (manual or mock).
6. Seller marks delivered with proof via `/deliver <deal_id> <proof>`.
7. Buyer releases or disputes (`/release <deal_id>` or `/dispute <deal_id> <reason>`).
8. Admin resolves disputes and executes release.
9. Deal closed and logged.

> **Rule:** If it is not written in the deal description, it is NOT part of the deal.

## Deal states
`DRAFT → CONFIRMED → FUNDED → DELIVERED → RELEASED / DISPUTED → CLOSED`

## Database tables
- `users`
- `deals`
- `payments`
- `disputes`
- `audit_logs`

## Setup
1. **Create a bot** with BotFather and get a token.
2. **Configure environment variables** (see `.env.example`).
3. **Install dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. **Run the bot:**
   ```bash
   python -m escrow_bot.bot
   ```

## Environment variables
- `BOT_TOKEN` – Telegram bot token.
- `ADMIN_IDS` – Comma-separated Telegram user IDs for admins.
- `DATABASE_PATH` – SQLite database path.
- `FEE_PERCENT` – Fee percentage (can be 0).
- `FEE_FLAT` – Flat fee (can be 0).
- `MAX_DEAL_AMOUNT` – Maximum deal amount.
- `MAX_ACTIVE_DEALS_PER_USER` – Limit active deals per user.
- `DEAL_CREATE_RATE_LIMIT_SECONDS` – Rate limiting window for new deals.
- `MOCK_BLOCKCHAIN` – `true` to enable mock deposit command.
- `LOG_LEVEL` – Log verbosity (e.g., `INFO`).
- `TON_DEPOSIT_ADDRESS` – Deposit address for TON.
- `USDT_TON_DEPOSIT_ADDRESS` – Deposit address for USDT on TON.
- `USDT_TRC20_DEPOSIT_ADDRESS` – Deposit address for USDT on TRON.

## Manual testing (Mock Blockchain Mode)
Use mock mode for safe testing with no real funds:
1. Set `MOCK_BLOCKCHAIN=true` in `.env`.
2. Start the bot.
3. Create a deal and confirm it.
4. As the buyer or admin, simulate a deposit:
   ```
   /mockdeposit <deal_id> mock-tx-001
   ```
5. Seller delivers:
   ```
   /deliver <deal_id> https://example.com/proof
   ```
6. Buyer releases:
   ```
   /release <deal_id>
   ```
   Or open a dispute:
   ```
   /dispute <deal_id> Delivery issue details
   ```

## Automated tests
Run all tests:
```bash
pytest
```

## Security notes & limitations
- Admin-only release and dispute resolution.
- No private key handling or automatic payouts.
- Strong input validation and permission checks.
- Immutable deal terms after both parties confirm.
- All actions are audit-logged for traceability.

## Project structure
```
escrow_bot/
  bot.py
  config.py
  constants.py
  db.py
  logging_config.py
  mock_blockchain.py
  models.py
  repositories.py
  services.py

tests/
  test_admin.py
  test_deals.py
  test_limits.py
  test_states.py
```
