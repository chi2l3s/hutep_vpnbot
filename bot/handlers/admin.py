"""Хендлеры админ-панели."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from bot.config import settings
from bot.db.models import User, Subscription, get_session_maker
from bot.utils.date_utils import days_from_now, extend_subscription, format_date

router = Router(name="admin")

# Храним выбор админа в памяти (для простоты)
_admin_state = {}


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом."""
    return user_id in settings.admin_list


@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery) -> None:
    """Главная админ-панель."""
    if not is_admin(callback.from_user.id):
        await callback.message.answer("⛔ У вас нет доступа к админ-панели.")
        return

    text = (
        "👨‍💻 <b>Админ-панель HutepVPN</b>\n\n"
        "🛠 Выберите действие:"
    )

    from bot.keyboards.inline import get_admin_keyboard

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery) -> None:
    """Список последних пользователей."""
    if not is_admin(callback.from_user.id):
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        from sqlalchemy import select, func

        # Общая статистика
        total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
        active_subs = (await session.execute(
            select(func.count(Subscription.id)).where(Subscription.is_active == True)
        )).scalar() or 0

        # Последние 10 пользователей
        users = (await session.execute(
            select(User).order_by(User.created_at.desc()).limit(10)
        )).scalars().all()

        text = (
            f"👥 <b>Статистика</b>\n"
            f"📊 Всего: {total_users}\n"
            f"✅ Подписок: {active_subs}\n\n"
            f"<b>Последние пользователи:</b>\n"
        )

        for user in users:
            sub = await session.get(Subscription, user.id)
            sub_text = "✅ Активна" if sub and sub.is_valid else "❌ Нет"
            days = sub.days_remaining if sub and sub.is_valid else 0
            text += f"\n👤 {user.full_name}\n"
            text += f"   🆔 {user.id} | 📅 {sub_text} ({days} дн.)\n"

    from bot.keyboards.inline import get_admin_users_keyboard

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_users_keyboard(),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_user_"))
async def admin_user_actions(callback: CallbackQuery) -> None:
    """Действия с конкретным пользователем."""
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
            f"🆔 ID: <code>{user.id}</code>\n"
            f"📅 Регистрация: {format_date(user.created_at)}\n"
        )

        if sub and sub.is_valid:
            from bot.utils.date_utils import format_days_remaining
            text += f"\n📊 <b>Подписка:</b>\n"
            text += f"   📅 Осталось: {format_days_remaining(sub.days_remaining)}\n"
            text += f"   📆 Истекает: {format_date(sub.end_date)}"
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
        await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_give_days_"))
async def admin_select_days(callback: CallbackQuery) -> None:
    """Выбор количества дней для выдачи."""
    if not is_admin(callback.from_user.id):
        return

    user_id = int(callback.data.split("_")[3])

    _admin_state[callback.from_user.id] = {"target_user": user_id}

    text = (
        f"🎁 <b>Выберите количество дней</b>\n\n"
        f"🆔 Пользователь: <code>{user_id}</code>"
    )

    from bot.keyboards.inline import get_admin_days_keyboard

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_days_keyboard(user_id),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm_give(callback: CallbackQuery) -> None:
    """Подтверждение выдачи подписки."""
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
            f"🆔 {user_id}\n"
            f"📅 +{days} дней",
            parse_mode="HTML"
        )


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery) -> None:
    """Статистика бота."""
    if not is_admin(callback.from_user.id):
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        from sqlalchemy import select, func

        total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
        active_subs = (await session.execute(
            select(func.count(Subscription.id)).where(Subscription.is_active == True)
        )).scalar() or 0

        text = (
            "📊 <b>Статистика</b>\n\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"✅ Активных подписок: {active_subs}\n"
            f"❌ Без подписок: {total_users - active_subs}\n"
            f"💰 Конверсия: {(active_subs / total_users * 100) if total_users > 0 else 0:.1f}%"
        )

    try:
        await callback.message.edit_text(text, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, parse_mode="HTML")


@router.message(F.text == "/admin_give")
async def admin_give_info(message: Message) -> None:
    """Команда /admin_give - информация."""
    if not is_admin(message.from_user.id):
        return

    # Показываем список последних пользователей для быстрого выбора
    session_maker = get_session_maker()
    async with session_maker() as session:
        users = (await session.execute(
            select(User).order_by(User.created_at.desc()).limit(5)
        )).scalars().all()

        text = "🎁 <b>Выдача подписки</b>\n\nВыберите пользователя или введите:\n<code>/admin_give [id] [дни]</code>\n\n<b>Последние пользователи:</b>\n"

        for user in users:
            sub = await session.get(Subscription, user.id)
            status = "✅" if sub and sub.is_valid else "❌"
            text += f"\n{status} {user.full_name} ({user.id})"

    from bot.keyboards.inline import get_admin_keyboard

    await message.answer(text, parse_mode="HTML")


@router.message(F.text.like("/admin_give %"))
async def admin_give_command(message: Message) -> None:
    """Выдача подписки: /admin_give <user_id> <days>"""
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
        await message.answer(f"❌ Доступные дни: {', '.join(map(str, settings.subscription_plans.keys()))}")
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
            f"👤 {user.full_name} ({user_id})\n"
            f"📅 +{days} дней",
            parse_mode="HTML"
        )
