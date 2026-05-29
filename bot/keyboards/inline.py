"""Inline клавиатуры для бота."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import settings


# ─────────────────────────────────────────────────────────────
# Главное меню (inline)
# ─────────────────────────────────────────────────────────────

def get_main_menu_inline_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Главное меню с inline-кнопками."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🖥 Мой кабинет", callback_data="cabinet"),
        InlineKeyboardButton(text="📊 Статус подписки", callback_data="subscription_status"),
    )
    builder.row(
        InlineKeyboardButton(text="🔐 VPN профили", callback_data="vpn_profiles"),
        InlineKeyboardButton(text="💳 Оформить подписку", callback_data="subscribe"),
    )
    builder.row(
        InlineKeyboardButton(text="👥 Рефералы", callback_data="referral_info"),
        InlineKeyboardButton(text="📖 Помощь", callback_data="help"),
    )

    if is_admin:
        builder.row(
            InlineKeyboardButton(text="🛠 Админ-панель", callback_data="admin_panel")
        )

    return builder.as_markup()


# ─────────────────────────────────────────────────────────────
# Inline-клавиатуры подписок
# ─────────────────────────────────────────────────────────────

def get_subscription_plans_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора тарифного плана."""
    builder = InlineKeyboardBuilder()

    for days, plan in settings.subscription_plans.items():
        price = plan["price"]
        name = plan["name"]
        badge = " 👑" if days == 360 else (" ⭐" if days == 180 else (" 🔥" if days == 90 else ""))
        btn_text = f"{days} дней — {price}₽{badge}"

        builder.row(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"sub_select_{days}"
        ))

    builder.row(
        InlineKeyboardButton(text="🔙 В меню", callback_data="menu_main")
    )
    return builder.as_markup()


def get_payment_methods_keyboard(days: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора способа оплаты."""
    builder = InlineKeyboardBuilder()

    plan = settings.subscription_plans.get(days, {})
    price = plan.get("price", 0)

    builder.row(InlineKeyboardButton(
        text=f"⭐ Telegram Stars ({price}₽)",
        callback_data=f"pay_stars_{days}"
    ))
    builder.row(InlineKeyboardButton(
        text=f"₿ Криптовалюта ({price}₽)",
        callback_data=f"pay_crypto_{days}"
    ))
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"sub_select_{days}")
    )
    return builder.as_markup()


def get_back_to_subscription_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата к выбору подписки."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Другой тариф", callback_data="subscribe"),
        InlineKeyboardButton(text="🔙 В меню", callback_data="menu_main")
    )
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────
# Inline-клавиатуры профиля
# ─────────────────────────────────────────────────────────────

def get_profile_keyboard(has_subscription: bool) -> InlineKeyboardMarkup:
    """Клавиатура личного кабинета."""
    builder = InlineKeyboardBuilder()

    if has_subscription:
        builder.row(
            InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="subscribe")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="💳 Купить подписку", callback_data="subscribe")
        )

    builder.row(
        InlineKeyboardButton(text="🔗 Мой реф. код", callback_data="referral_info")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 В меню", callback_data="menu_main")
    )
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────
# Прочие Inline-клавиатуры
# ─────────────────────────────────────────────────────────────

def get_referral_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура реферальной программы."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Как это работает?", callback_data="referral_help")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 В меню", callback_data="menu_main")
    )
    return builder.as_markup()


def get_vpn_profiles_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления VPN профилями."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📱 Показать профиль", callback_data="vpn_show"),
        InlineKeyboardButton(text="🔄 Обновить профиль", callback_data="vpn_regenerate"),
    )
    builder.row(
        InlineKeyboardButton(text="📖 Инструкция подключения", callback_data="vpn_instructions"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 В меню", callback_data="menu_main")
    )
    return builder.as_markup()


def get_help_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура помощи."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📡 Статус серверов", callback_data="help_servers"),
        InlineKeyboardButton(text="💬 Связаться с поддержкой", callback_data="help_support"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 В меню", callback_data="menu_main")
    )
    return builder.as_markup()


def get_confirm_payment_keyboard(payment_id: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения оплаты (для крипты)."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Проверить оплату",
            callback_data=f"check_payment_{payment_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отменить", callback_data="subscribe")
    )
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────
# Admin Inline-клавиатуры
# ─────────────────────────────────────────────────────────────

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура админ-панели."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
    )
    builder.row(
        InlineKeyboardButton(text="🎁 Выдать подписку", callback_data="admin_give"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 В меню", callback_data="menu_main")
    )
    return builder.as_markup()


def get_admin_give_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора дней для выдачи подписки."""
    builder = InlineKeyboardBuilder()
    for days in [30, 90, 180, 360]:
        builder.row(InlineKeyboardButton(
            text=f"{days} дней — {settings.subscription_plans.get(days, {}).get('price', '?')}₽",
            callback_data=f"admin_select_user_{days}"
        ))
    return builder.as_markup()


def admin_users_list_keyboard(users) -> InlineKeyboardMarkup:
    """Клавиатура со списком пользователей для админа."""
    builder = InlineKeyboardBuilder()
    for user in users[:20]:  # Лимит 20 пользователей
        builder.row(InlineKeyboardButton(
            text=f"👤 {user.full_name} ({user.id})",
            callback_data=f"admin_user_{user.id}"
        ))
    return builder.as_markup()