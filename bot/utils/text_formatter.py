"""Утилиты для форматирования текста в боте."""

from bot.config import settings


def format_price(amount: float) -> str:
    """Форматирование цены."""
    return f"{amount:.0f}₽"


def format_subscription_text(subscription) -> str:
    """Форматирование текста статуса подписки."""
    from bot.utils.date_utils import format_date, format_days_remaining

    if not subscription or not subscription.is_valid:
        return "🚫 <b>Нет активной подписки</b>\n\nОформите подписку для доступа к VPN-серверам!"

    return (
        f"✅ <b>Подписка активна</b>\n\n"
        f"📅 Осталось: <b>{format_days_remaining(subscription.days_remaining)}</b>\n"
        f"📆 Истекает: <b>{format_date(subscription.end_date)}</b>"
    )


def format_referral_info(user, referral_count: int) -> str:
    """Форматирование информации о рефералах."""
    return (
        f"👥 <b>Реферальная программа</b>\n\n"
        f"📊 Приглашений: <b>{referral_count}</b>\n\n"
        f"🎁 <b>Бонус:</b> Пригласите друга — оба получите <b>+7 дней</b> подписки!\n\n"
        f"🔗 <b>Ваш код:</b>\n"
        f"<code>{user.referral_code}</code>\n\n"
        f"📨 <b>Ссылка:</b>\n"
        f"https://t.me/{settings.bot_token.split(':')[0] if ':' in settings.bot_token else 'bot'}?start={user.referral_code}"
    )


def format_profile_info(profile) -> str:
    """Форматирование VPN профиля."""
    return (
        f"🔐 <b>VPN Профиль</b>\n\n"
        f"⚙️ Протокол: <b>{profile.protocol.upper()}</b>\n"
        f"🖥 Сервер: <b>{profile.server_name or 'Неизвестен'}</b>\n"
        f"📋 Статус: <b>{'Активен' if profile.is_active else 'Неактивен'}</b>"
    )
