# Escrow Telegram Bot

A **safe, minimal, production-ready escrow facilitator** built on `python-telegram-bot` v21 (async). This bot is **not** a wallet, exchange, bank, or marketplace. All interactions are private bot chats, and **admin-controlled release** is mandatory.

## What this bot does
- Facilitates escrow deals between a buyer and seller.
- Records immutable terms, proof requirements, and audit logs.
- Supports admin-only dispute resolution and payout execution.
- Verifies deposits for TON/USDT(TON) and USDT(TRC20).

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

## UI Navigation
- `/start` or `/menu` shows the main Gen‑Z Premium menu.
- **🧾 New Deal** starts the guided wizard (button-first).
- **📂 My Deals** lists your latest 10 deals with quick actions.
- Deal details show state-aware actions like **Deposit**, **Deliver**, **Release**, and **Dispute**.

## Escrow flow
1. `/start` → menu and rules.
2. `/newdeal` wizard:
   - Role selection
   - Counterparty @username
   - Deal title
   - Detailed description (vague input rejected)
   - Proof type selection
   - Currency & network
   - Amount
   - Full summary + fee + risk warnings
3. Counterparty confirms via `/confirmdeal <deal_id>`.
4. Buyer deposits using the displayed instructions (memo required on TON).
5. Deposit verified automatically (TON) or via TRC20 tx hash.
6. Seller delivers proof.
7. Buyer releases or disputes.
8. Admin resolves disputes and executes payout.
9. Deal closed and logged.

> **Rule:** If it is not written in the deal description, it is NOT part of the deal.

## Deal states
`DRAFT → CONFIRMED → FUNDED → DELIVERED → RELEASED / DISPUTED → CLOSED`

## Deposit verification
### TON + USDT (TON)
- Requires memo/comment: `DEAL-<deal_id>`.
- Automatic watcher polls for:
  - destination address
  - memo/comment
  - exact amount
  - required confirmations

### USDT (TRC20)
- Buyer submits tx hash via **🧾 Submit Tx Hash**.
- Bot validates via TRON explorer API:
  - token is USDT (TRC20)
  - receiver address matches escrow address
  - amount matches expected
  - confirmations meet minimum

## Fees / commission split
- Fee = `fee_percent` + `fee_flat`.
- Buyer sees fee + seller receive amount before confirming.
- On payout, seller receives `amount - fee`.
- Fee goes to the configured fee wallet per network.
- Payout execution is **admin-controlled**.

## Channel logs
- **Private log channel**: full details (usernames, deal_id, amounts, tx hash).
- **Public log channel**: masked summary only (no usernames, no terms).
- Masking modes:
  - `masked`: `@ab***yz`, `9a3f...b21c`
  - `extra`: `@a***`, `9a3f...`
- All log dispatches are toggleable by admin and never crash the bot.

## Admin Panel
Open `/admin` to access:
- **Deals / Disputes** quick entry points
- **Fees** & **Limits** editable in‑bot
- **Logs** toggles + test messages
- **Config** (maintenance mode, channels, support, wallets, confirmations)

All destructive actions show a confirmation screen.

## Environment variables
Required:
- `BOT_TOKEN`
- `ADMIN_IDS`

Defaults (synced into DB settings on first run):
- `FEE_PERCENT`, `FEE_FLAT`
- `MAX_DEAL_AMOUNT`, `MAX_ACTIVE_DEALS_PER_USER`, `DEAL_CREATE_RATE_LIMIT_SECONDS`
- `TON_DEPOSIT_ADDRESS`, `USDT_TON_DEPOSIT_ADDRESS`, `USDT_TRC20_DEPOSIT_ADDRESS`
- `FEE_WALLET_TON`, `FEE_WALLET_USDT_TON`, `FEE_WALLET_USDT_TRC20`
- `UPDATES_CHANNEL_URL`, `VOUCHES_CHANNEL_URL`, `SUPPORT_USERNAME_OR_URL`
- `PRIVATE_LOG_CHANNEL_ID`, `PUBLIC_LOG_CHANNEL_ID`
- `CONFIRMATIONS_REQUIRED_TON`, `CONFIRMATIONS_REQUIRED_TRON`
- `TON_API_URL`, `TON_API_KEY`, `TRON_API_URL`

### Admin-editable settings (no code edits)
- `fee_percent`, `fee_flat`
- `max_deal_amount`, `max_active_deals_per_user`, `rate_limit_seconds`
- `private_log_channel_id`, `public_log_channel_id`
- `updates_channel_url`, `vouches_channel_url`, `support_username_or_url`
- `fee_wallet_ton`, `fee_wallet_usdt_ton`, `fee_wallet_usdt_trc20`
- `confirmations_required_ton`, `confirmations_required_tron`
- `ton_deposit_address`, `usdt_ton_deposit_address`, `usdt_trc20_deposit_address`

## Manual testing (mock mode)
Set `MOCK_BLOCKCHAIN=true` and use:
```
/mockdeposit <deal_id> mock-tx-001
```
Then continue with deliver → release/dispute.

## Automated tests
Run all tests:
```bash
pytest
```

## Project structure
```
escrow_bot/
  bot.py
  config.py
  constants.py
  deposit_service.py
  logging_config.py
  logging_service.py
  models.py
  repositories.py
  services.py
  settings_store.py
  ui_text.py

tests/
  test_admin.py
  test_deals.py
  test_limits.py
  test_logging_service.py
  test_masking.py
  test_settings.py
  test_states.py
  test_ton_memo.py
  test_tron_validator.py
```
