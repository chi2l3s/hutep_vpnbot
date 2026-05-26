"""Точка входа для бота HutepVPN."""

import asyncio
import logging
import os
import re
import sys

# Force unbuffered output on Windows
os.environ["PYTHONUNBUFFERED"] = "1"
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import web

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Создаём папку для БД
os.makedirs("data", exist_ok=True)

from bot.config import settings
from bot.db import init_db, close_db, get_session_maker
from bot.db.models import Subscription
from bot.handlers import start, menu, subscription, referral, payment

# Настройка логирования
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
handler.flush = lambda: None  # disable buffering
root_logger.addHandler(handler)
logger = logging.getLogger(__name__)

print("Step 1: Imports done", flush=True)

# ─────────────────────────────────────────────────────────────
# Бот и диспетчер
# ─────────────────────────────────────────────────────────────

print("Step 2: Creating bot...", flush=True)

# Прокси для Telegram (из .env)
proxy = settings.proxy if hasattr(settings, 'proxy') and settings.proxy else None
if proxy:
    print(f"Using proxy: {proxy[:50]}...", flush=True)
    session = AiohttpSession(proxy=proxy)
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML), session=session)
else:
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

print("Step 3: Bot created", flush=True)

dp = Dispatcher()
print("Step 4: Dispatcher created", flush=True)

dp.include_routers(
    start.router,
    menu.router,
    subscription.router,
    referral.router,
    payment.router,
)
print("Step 5: Routers included", flush=True)


# ─────────────────────────────────────────────────────────────
# Webhook для NOWPayments
# ─────────────────────────────────────────────────────────────

async def handle_nowpayments_webhook(request: web.Request) -> web.Response:
    try:
        payload = await request.json()
        logger.info(f"NOWPayments webhook: {payload}")

        from bot.services.payment_service import get_payment_service
        payment_svc = get_payment_service()
        success = await payment_svc.handle_nowpayments_webhook(payload)

        if success:
            order_id = payload.get("order_id", "")
            if order_id.startswith("hv_"):
                parts = order_id.split("_")
                if len(parts) >= 2:
                    user_id = int(parts[1])
                    days_desc = payload.get("order_description", "")
                    match = re.search(r"(\d+)\s*дней", days_desc)
                    if match:
                        await _activate_subscription_webhook(user_id, int(match.group(1)))

        return web.Response(status=200, text="OK")
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return web.Response(status=500, text="Error")


async def _activate_subscription_webhook(user_id: int, days: int) -> None:
    from datetime import datetime
    from sqlalchemy import select
    from bot.utils.date_utils import days_from_now, extend_subscription

    session_maker = get_session_maker()
    async with session_maker() as session:
        stmt = select(Subscription).where(Subscription.user_id == user_id)
        result = await session.execute(stmt)
        subscription = result.scalar_one_or_none()

        now = datetime.utcnow()

        if subscription and subscription.is_valid:
            subscription.end_date = extend_subscription(subscription.end_date, days)
            subscription.days += days
        else:
            subscription = Subscription(
                user_id=user_id,
                days=days,
                start_date=now,
                end_date=days_from_now(days),
                is_active=True,
            )
            session.add(subscription)

        await session.commit()

        try:
            await bot.send_message(
                user_id,
                f"🎉 <b>Подписка активирована!</b>\n\n"
                f"✅ +{days} дней добавлено к вашей подписке!",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")


async def on_startup() -> None:
    print("Startup: initializing DB...", flush=True)
    await init_db()
    print("Startup: DB initialized", flush=True)
    if settings.webhook_host:
        path = settings.webhook_path or "/webhook"
        await bot.set_webhook(f"{settings.webhook_host}{path}")
        print("Startup: Webhook set", flush=True)


async def on_shutdown() -> None:
    print("Shutdown: closing bot...", flush=True)
    await bot.session.close()
    await close_db()
    print("Shutdown: done", flush=True)


def main() -> None:
    print("HutepVPN Bot starting...", flush=True)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    print("Handlers registered", flush=True)

    if settings.webhook_host:
        print("Webhook mode", flush=True)
        app = web.Application()
        app.router.add_post("/webhook/nowpayments", handle_nowpayments_webhook)

        async def telegram_webhook(request: web.Request) -> web.Response:
            from aiogram.types import Update
            try:
                data = await request.json()
                update = Update.model_validate(data)
                await dp.feed_webhook_update(bot, update)
                return web.Response(status=200)
            except Exception as e:
                logger.error(f"Webhook error: {e}")
                return web.Response(status=500)

        webhook_path = settings.webhook_path or "/webhook"
        app.router.add_post(webhook_path, telegram_webhook)
        web.run_app(app, host=settings.webapp_host, port=settings.webapp_port, print=None)
    else:
        print("Starting polling...", flush=True)
        asyncio.run(dp.start_polling(bot, close_bot_session=True))


if __name__ == "__main__":
    main()