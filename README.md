# Premium Telegram Crypto Escrow Bot

A production-grade escrow facilitator for Telegram. It is **not** an exchange or marketplace, and nothing here is legal advice. Users must accept Terms before using the bot.

## Features
- Strict deal state machine (no broken flows).
- Anti-fake deposits: on-chain verification and tx hash uniqueness.
- Anti-spam: rate limits, captcha, signed callbacks, risk scoring foundation.
- Admin panel controls automation, payouts, limits, logs, and settings.
- Group pool support for private deal rooms (bot API compliant).
- Docker-first deployment with backups and scripts.

## Supported assets
- TON (native)
- USDT on TON
- USDT on TRON (TRC20)

## Safety & compliance
- Wrong network/address = irreversible loss.
- Disputes decided using Terms + Proof only.
- Admin may pause/deny service.

## Local setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run
```bash
python -m escrow_bot.app
```

## Testing
```bash
pytest
ruff check escrow_bot tests
```

## Deploy on VPS with Docker
1. Provision a server and install Docker + Compose:
   ```bash
   scripts/setup_ubuntu.sh
   ```
2. Configure `.env` with your bot token and addresses.
3. Build and start:
   ```bash
   docker compose build
   docker compose up -d
   ```
4. Tail logs:
   ```bash
   docker compose logs -f
   ```

### Database backups
- Manual backup:
  ```bash
  scripts/backup.sh
  ```
- Makefile backup:
  ```bash
  make backup-db
  ```
- Restore:
  ```bash
  make restore-db FILE=backups/escrow-<timestamp>.db
  ```

## Architecture
- `escrow_bot/ui/` holds all UI constants, icons, keyboards, and renderers.
- `escrow_bot/utils/` provides security helpers, validation, and state machine.
- `escrow_bot/services/` contains DB access, settings, payout queue, and chain verifiers.

## Disclaimer
This project is an escrow facilitator for user-to-user deals. It does not custody funds, does not match buyers/sellers, and provides no legal advice.
