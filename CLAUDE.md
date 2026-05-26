# HutepVPN Bot — Documentation

## Overview

This is a Telegram bot for managing VPN subscriptions with:
- Personal cabinet
- VPN profile management via X-UI API
- Payments (Telegram Stars + Cryptocurrency via NOWPayments)
- Referral system (+7 days per friend)

## Architecture

### Stack
- Python 3.11+
- Aiogram 3 (async Telegram bot framework)
- SQLAlchemy + aiosqlite (database)
- FastAPI/uvicorn (webhook server)

### Key Files

| File | Purpose |
|------|---------|
| `bot/main.py` | Entry point, bot initialization |
| `bot/config.py` | Configuration via environment variables |
| `bot/db/models.py` | SQLAlchemy models (User, Subscription, Payment, VPNProfile) |
| `bot/handlers/` | Aiogram routers for commands and callbacks |
| `bot/services/` | Business logic (X-UI, payments, VPN, referrals) |
| `bot/keyboards/inline.py` | Inline and reply keyboards |

### Database Models

- **User** — Telegram user info, referral code
- **Subscription** — active subscription with dates
- **Payment** — payment records (stars/crypto)
- **VPNProfile** — user's VPN configuration

## Configuration

See `.env.example`:
- `BOT_TOKEN` — Telegram bot token from @BotFather
- `XUI_API_URL` / `XUI_API_KEY` — X-UI panel credentials
- `NOWPAYMENTS_API_KEY` — NOWPayments API key
- `DATABASE_URL` — SQLite connection string

## Development

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
python -m bot.main
```

## Commands

- `/start` — Welcome + registration (checks referral code)
- `/menu` — Main menu
- `/subscribe` — Subscription plans
- `/referral` — Referral program
- `/help` — Help

## Payment Flow

### Telegram Stars
1. User selects plan → `pay_stars_*` callback
2. Bot sends invoice via `SendInvoice`
3. User pays → `pre_checkout_query` → `successful_payment`
4. Subscription activated, referral bonus applied

### Cryptocurrency (NOWPayments)
1. User selects plan → `pay_crypto_*` callback
2. Bot creates invoice via NOWPayments API
3. User pays on external page
4. NOWPayments sends webhook → subscription activated

## X-UI Integration

Uses custom aiohttp client to communicate with X-UI panel:
- `create_client()` — create VLESS client
- `get_clients()` — list clients
- `delete_client()` — remove client
- `generate_vless_link()` — generate connection link

## Referral System

- Auto-generated code on registration (`HV-XXXXXX`)
- When referral purchases → both get +7 days
- Applied via `apply_referral_bonus()` in `referral_service.py`