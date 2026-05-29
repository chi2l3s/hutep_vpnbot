"""Хендлеры админ-панели."""

import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from bot.config import settings
from bot.db.models import User, Subscription, get_session_maker
from bot.utils.date_utils import days_from_now, extend_subscription, format_date, format_days_remaining

logger = logging.getLogger(__name__)

router = Router(name="admin")


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_list


# ─── Helpers ───────────────────────────────────────────────────────────

def _get_or_create_vpn_client(xui, email: str, inbound_ids: list[int]) -> tuple[str | None, str | None]:
    """Создать клиента в X-UI или получить существующего. Возвращает (sub_id, subscription_url)."""
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            client = loop.run_until_complete(xui.get_client(email))
            if client:
                sub_id = client.get("subId") or email
            else:
                result = loop.run_until_complete(xui.create_client(email=email, inbound_ids=inbound_ids))
                if result and result.get("success"):
                    sub_id = email
                else:
                    return None, None
        finally:
            loop.close()

        sub_id = sub_id or email
        url = xui.generate_subscription_url(sub_id)
        return sub_id, url
    except Exception as e:
        logger.error(f"X-UI error: {e}")
        return None, None


# ─── Handlers ────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.message.answer("⛔ Нет доступа.")
        return

    text = "👨‍💻 <b>Админ-панель</b>\n\nВыберите:"
    from bot.keyboards.inline import get_admin_keyboard
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        from sqlalchemy import select, func
        total = (await session.execute(select(func.count(User.id))).scalar() or 0
        active = (await session.execute(
            select(func.count(Subscription.id)).where(Subscription.is_active == True)
        ).scalar() or 0

        users = (await session.execute(
            select(User).order_by(User.created_at.desc()).limit(10)
        )).scalars().all()

    text = (
            f"👥 <b>Пользователи</b>\n\n"
            f"📊 Всего: {total} | ✅ Подписок: {active}\n\n"
            f"<b>Нажмите на пользователя:</b>"
    )
    from bot.keyboards.inline import get_admin_users_keyboard
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_users_keyboard(users),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_admin_users_keyboard(users),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("admin_user_"))
async def admin_user_actions(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return

    user_id = int(callback.data.split("_")[2])

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await session.get(User, user_id)
        if not user:
            await callback.message.answer(f"❌ Не найден.")
            return

        sub = await session.get(Subscription, user_id)

        text = (
            f"👤 <b>{user.full_name}</b>\n"
            f"🆔 <code>{user.id}</code>\n"
            f"📅 Регистрация: {format_date(user.created_at)}\n"
        )
        if sub and sub.is_valid:
            text += (
                f"\n✅ <b>Подписка:</b>\n"
                f"   📅 Осталось: {format_days_remaining(sub.days_remaining)}\n"
                f"   📆 Истекает: {format_date(sub.end_date)}"
            )
        else:
            text += f"\n🚫 <b>Нет подписки</b>"

    from bot.keyboards.inline import get_admin_user_actions_keyboard
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_user_actions_keyboard(user_id),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_admin_user_actions_keyboard(user_id),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm_give(callback: CallbackQuery) -> None:
    """Выдача подписки + VPN клиент в X-UI."""
    if not is_admin(callback.from_user.id):
        return

    parts = callback.data.split("_")
    user_id = int(parts[2])
    days = int(parts[3])

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await session.get(User, user_id)
        if not user:
            await callback.message.answer(f"❌ Пользователь {user_id} не найден.")
            return

        sub = await session.get(Subscription, user_id)
        if sub:
            sub.days = days
            sub.start_date = days_from_now(0)
            sub.end_date = days_from_now(days)
            sub.is_active = True
        else:
            sub = Subscription(
                user_id=user_id,
                days=days,
                start_date=days_from_now(0),
                end_date=days_from_now(days),
                is_active=True,
            )
            session.add(sub)
        await session.commit()
        await session.refresh(sub)
        full_name = user.full_name

    # X-UI: получить inbound IDs
    from bot.services.xui_service import get_xui_service
    xui = get_xui_service()
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        inbounds = loop.run_until_complete(xui.get_inbounds_options())
    finally:
        loop.close()

    inbound_ids = [ib["id"] for ib in inbounds if ib.get("id")]
    if not inbound_ids:
        inbound_ids = [1]

    sub_id, sub_url = _get_or_create_vpn_client(xui, str(user_id), inbound_ids)

    if sub_url:
        vpn_text = f"\n\n🔗 <b>VPN:</b>\n<code>{sub_url}</code>"
    else:
        vpn_text = "\n\n⚠️ VPN-клиент не создан (X-UI недоступен)"

    await callback.message.answer(
        f"✅ <b>Подписка выдана!</b>\n\n"
        f"👤 {full_name}\n"
        f"🆔 <code>{user_id}</code>\n"
        f"📅 +{days} дней{vpn_text}",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        from sqlalchemy import select, func
        total = (await session.execute(select(func.count(User.id))).scalar() or 0
        active = (await session.execute(
            select(func.count(Subscription.id)).where(Subscription.is_active == True)
        ).scalar() or 0

    conv = active / total * 100 if total else 0
    text = (
        "📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: {total}\n"
        f"✅ Подписок: {active}\n"
        f"❌ Без подписок: {total - active}\n"
        f"💰 Конверсия: {conv:.1f}%"
    )
    from bot.keyboards.inline import get_admin_keyboard
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")


@router.message(F.text.like("/admin_give %"))
async def admin_give_cmd(message: Message) -> None:
    """ /admin_give <user_id> <days>"""
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            "📖 <b>Использование:</b>\n"
            "<code>/admin_give [id] [дни]</code>\n\n"
            "Пример: <code>/admin_give 123456789 30</code>"
        )
        return

    try:
        user_id = int(parts[1])
        days = int(parts[2])
    except ValueError:
        await message.answer("❌ Неверный формат")
        return

    if days not in settings.subscription_plans:
        await message.answer(
            f"❌ Доступные дни: {', '.join(map(str, settings.subscription_plans.keys())}"
        )
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer(f"❌ Пользователь {user_id} не найден")
            return

        sub = await session.get(Subscription, user_id)
        if sub:
            sub.days = days
            sub.start_date = days_from_now(0)
            sub.end_date = days_from_now(days)
            sub.is_active = True
        else:
            sub = Subscription(
                user_id=user_id,
                days=days,
                start_date=days_from_now(0),
                end_date=days_from_now(days),
                is_active=True,
            )
            session.add(sub)
        await session.commit()
        full_name = user.full_name

    from bot.services.xui_service import get_xui_service
    xui = get_xui_service()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        inbounds = loop.run_until_complete(xui.get_inbounds_options())
    finally:
        loop.close()

    inbound_ids = [ib["id"] for ib in inbounds if ib.get("id")] or [1]

    sub_id, sub_url = _get_create_vpn_client(xui, str(user_id), inbound_ids)

    if sub_url:
        vpn_text = f"\n\n🔗 <b>VPN:</b>\n<code>{sub_url}</code>"
    else:
        vpn_text = "\n\n⚠️ VPN не создан (X-UI недоступен)"

    await message.answer(
        f"✅ <b>Подписка выдана!</b>\n\n"
        f"👤 {full_name}\n"
        f"🆔 <code>{user_id}</code>\n"
        f"📅 +{days} дней{vpn_text}",
        parse_mode="HTML"
    )
