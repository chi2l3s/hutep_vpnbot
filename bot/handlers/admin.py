"""Хендлеры админ-панели."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from bot.config import settings
from bot.db.models import User, Subscription, get_session_maker
from bot.utils.date_utils import days_from_now, extend_subscription, format_date, format_days_remaining

router = Router(name="admin")


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом."""
    return user_id in settings.admin_list


@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery) -> None:
    """Главная админ-панель."""
    if not is_admin(callback.from_user.id):
        await callback.message.answer("⛔ У вас нет доступа к админ-панели.")
        return

    text = "👨‍💻 <b>Админ-панель</b>\n\nВыберите действие:"

    from bot.keyboards.inline import get_admin_keyboard

    try:
        await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery) -> None:
    """Список пользователей."""
    if not is_admin(callback.from_user.id):
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        from sqlalchemy import select, func

        total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
        active_subs = (await session.execute(
            select(func.count(Subscription.id)).where(Subscription.is_active == True)
        )).scalar() or 0

        users = (await session.execute(
            select(User).order_by(User.created_at.desc()).limit(10)
        )).scalars().all()

        text = (
            f"👥 <b>Пользователи</b>\n\n"
            f"📊 Всего: {total_users} | ✅ Подписок: {active_subs}\n\n"
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
    """Карточка пользователя."""
    if not is_admin(callback.from_user.id):
        return

    user_id = int(callback.data.split("_")[2])

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await session.get(User, user_id)
        if not user:
            await callback.message.answer(f"❌ Пользователь {user_id} не найден.")
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
            text += f"\n🚫 <b>Нет активной подписки</b>"

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
    """Выдача подписки."""
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

        if sub and sub.is_valid:
            sub.end_date = extend_subscription(sub.end_date, days)
            sub.days += days
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

        await callback.message.answer(
            f"✅ <b>Подписка выдана!</b>\n\n"
            f"👤 {user.full_name}\n"
            f"🆔 <code>{user_id}</code>\n"
            f"📅 +{days} дней",
            parse_mode="HTML"
        )


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery) -> None:
    """Статистика."""
    if not is_admin(callback.from_user.id):
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        from sqlalchemy import select, func

        total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
        active_subs = (await session.execute(
            select(func.count(Subscription.id)).where(Subscription.is_active == True)
        )).scalar() or 0

        conv = (active_subs / total_users * 100) if total_users > 0 else 0

        text = (
            "📊 <b>Статистика</b>\n\n"
            f"👥 Всего пользователей: <b>{total_users}</b>\n"
            f"✅ Активных подписок: <b>{active_subs}</b>\n"
            f"❌ Без подписок: <b>{total_users - active_subs}</b>\n"
            f"💰 Конверсия: <b>{conv:.1f}%</b>"
        )

        from bot.keyboards.inline import get_admin_keyboard

        try:
            await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")
        except Exception:
            await callback.message.answer(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")


@router.message(F.text.like("/admin_give %"))
async def admin_give_cmd(message: Message) -> None:
    """Команда /admin_give <user_id> <days>"""
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
            f"❌ Доступные дни: {', '.join(map(str, settings.subscription_plans.keys()))}"
        )
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer(f"❌ Пользователь {user_id} не найден")
            return

        sub = await session.get(Subscription, user_id)

        if sub and sub.is_valid:
            sub.end_date = extend_subscription(sub.end_date, days)
            sub.days += days
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

        await message.answer(
            f"✅ <b>Подписка выдана!</b>\n\n"
            f"👤 {user.full_name}\n"
            f"🆔 <code>{user_id}</code>\n"
            f"📅 +{days} дней",
            parse_mode="HTML"
        )
