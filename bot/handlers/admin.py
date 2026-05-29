"""Хендлеры админ-панели."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from bot.config import settings
from bot.db.models import User, Subscription, get_session_maker
from bot.utils.date_utils import days_from_now, format_date

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

    text = (
        "👨‍💻 <b>Админ-панель HutepVPN</b>\n\n"
        "🛠 <b>Управление:</b>\n"
        "• Просмотр пользователей\n"
        "• Выдача подписки без оплаты\n"
        "• Статистика\n\n"
        "Выберите действие:"
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
    """Список пользователей."""
    if not is_admin(callback.from_user.id):
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        from sqlalchemy import select, func
        from bot.db.models import User, Subscription

        # Количество пользователей
        count_result = await session.execute(select(func.count(User.id)))
        total_users = count_result.scalar() or 0

        # Количество подписок
        sub_result = await session.execute(
            select(func.count(Subscription.id)).where(Subscription.is_active == True)
        )
        active_subs = sub_result.scalar() or 0

        text = (
            "👥 <b>Пользователи</b>\n\n"
            f"📊 <b>Всего:</b> {total_users}\n"
            f"✅ <b>Активных подписок:</b> {active_subs}\n"
            f"❌ <b>Без подписки:</b> {total_users - active_subs}\n\n"
            "💡 Используйте /admin_give для выдачи подписки"
        )

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "admin_give")
async def admin_give(callback: CallbackQuery) -> None:
    """Выдача подписки - показывает инструкцию."""
    if not is_admin(callback.from_user.id):
        return

    text = (
        "🎁 <b>Выдача подписки без оплаты</b>\n\n"
        "📖 <b>Использование:</b>\n"
        "Отправьте команду:\n"
        "<code>/admin_give &lt;user_id&gt; &lt;days&gt;</code>\n\n"
        "Пример: <code>/admin_give 123456789 30</code>\n\n"
        "Где:\n"
        "• <code>123456789</code> — Telegram ID пользователя\n"
        "• <code>30</code> — количество дней (30/90/180/360)"
    )

    try:
        await callback.message.edit_text(text, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, parse_mode="HTML")


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
            "📊 <b>Статистика HutepVPN</b>\n\n"
            f"👥 Всего пользователей: <b>{total_users}</b>\n"
            f"✅ Активных подписок: <b>{active_subs}</b>\n"
            f"💰 Конверсия: <b>{(active_subs / total_users * 100) if total_users > 0 else 0:.1f}%</b>"
        )

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(text, parse_mode="HTML")


@router.message(F.text == "/admin_give")
async def admin_give_command(message: Message) -> None:
    """Команда выдачи подписки: /admin_give <user_id> <days>"""
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            "📖 <b>Использование:</b>\n"
            "<code>/admin_give &lt;user_id&gt; &lt;days&gt;</code>\n\n"
            "Пример: <code>/admin_give 123456789 30</code>",
            parse_mode="HTML"
        )
        return

    try:
        user_id = int(parts[1])
        days = int(parts[2])
    except ValueError:
        await message.answer("❌ Неверный формат. Используйте: /admin_give &lt;user_id&gt; &lt;days&gt;")
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer(f"❌ Пользователь {user_id} не найден.")
            return

        subscription = await session.get(Subscription, user_id)

        if subscription and subscription.is_valid:
            from bot.utils.date_utils import extend_subscription
            subscription.end_date = extend_subscription(subscription.end_date, days)
            subscription.days += days
        else:
            subscription = Subscription(
                user_id=user_id,
                days=days,
                start_date=days_from_now(0),
                end_date=days_from_now(days),
                is_active=True,
            )
            session.add(subscription)

        await session.commit()

        await message.answer(
            f"✅ <b>Подписка выдана!</b>\n\n"
            f"👤 Пользователь: {user.full_name}\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"📅 Дней добавлено: <b>{days}</b>",
            parse_mode="HTML"
        )