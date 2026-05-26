"""Утилиты для работы с датами."""

from datetime import datetime, timedelta


def days_from_now(days: int) -> datetime:
    """Получить дату через N дней от текущего момента."""
    return datetime.utcnow() + timedelta(days=days)


def extend_subscription(current_end: datetime, additional_days: int) -> datetime:
    """Продлить подписку. Если истекла — начать с текущей даты."""
    now = datetime.utcnow()
    if current_end < now:
        return days_from_now(additional_days)
    return current_end + timedelta(days=additional_days)


def format_days_remaining(days: int) -> str:
    """Форматирование оставшихся дней с учётом склонения."""
    if days == 0:
        return "менее 1 дня"
    if days == 1:
        return "1 день"
    if 2 <= days <= 4:
        return f"{days} дня"
    return f"{days} дней"


def format_date(dt: datetime) -> str:
    """Форматирование даты в читаемый вид."""
    return dt.strftime("%d.%m.%Y")


def format_datetime(dt: datetime) -> str:
    """Форматирование даты и времени."""
    return dt.strftime("%d.%m.%Y в %H:%M")
