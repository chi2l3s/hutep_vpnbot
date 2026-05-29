"""Хендлер команды /start."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from bot.db.models import User, get_session_maker
from bot.services.referral_service import get_referral_service
from bot.keyboards.inline import get_main_menu_inline_keyboard
from bot.config import settings

router = Router(name="start")


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом."""
    return user_id in settings.admin_list


async def ensure_user_exists(message: Message) -> User | None:
    """Проверка и создание пользователя в БД."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        user_id = message.from_user.id
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            # Обновляем данные если изменились
            if user.username != message.from_user.username or user.full_name != message.from_user.full_name:
                user.username = message.from_user.username
                user.full_name = message.from_user.full_name
                await session.commit()
            return user

        # Создаём нового пользователя
        referrer = None
        if message.text and len(message.text.split()) > 1:
            ref_code = message.text.split()[1]
            referral_svc = get_referral_service()
            referrer = await referral_svc.get_user_by_referral_code(session, ref_code)

        try:
            user = User(
                id=user_id,
                username=message.from_user.username,
                full_name=message.from_user.full_name,
                referral_code=User.generate_referral_code(),
                referred_by=referrer.id if referrer else None,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
        except Exception:
            # Пользователь уже существует (race condition)
            await session.rollback()
            result = await session.execute(stmt)
            return result.scalar_one_or_none()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Обработчик команды /start."""
    await state.clear()

    user = await ensure_user_exists(message)
    if not user:
        await message.answer(
            "😔 Произошла ошибка при регистрации. Попробуйте позже.",
            parse_mode="HTML"
        )
        return

    welcome_text = (
        f"👋 <b>Добро пожаловать в HutepVPN!</b>\n\n"
        f"🛡 Надёжная защита вашего интернет-соединения.\n"
        f"⚡ Высокая скорость и стабильность.\n\n"
        f"✨ Привет, <b>{message.from_user.first_name}</b>!\n\n"
        f"Выберите действие:"
    )

    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_inline_keyboard(is_admin=is_admin(message.from_user.id)),
        parse_mode="HTML"
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    """Возврат в главное меню."""
    await state.clear()
    menu_text = (
        "📱 <b>Главное меню HutepVPN</b>\n\n"
        "Выберите действие:"
    )
    await message.answer(
        menu_text,
        reply_markup=get_main_menu_inline_keyboard(is_admin=is_admin(message.from_user.id)),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "menu_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат в главное меню."""
    await state.clear()
    text = "📱 <b>Главное меню HutepVPN</b>\n\nВыберите действие:"
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_main_menu_inline_keyboard(is_admin=is_admin(callback.from_user.id)),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_main_menu_inline_keyboard(is_admin=is_admin(callback.from_user.id)),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "cabinet")
async def cabinet_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Личный кабинет через inline-кнопку."""
    from bot.handlers import menu
    await state.clear()
    await menu.my_cabinet(callback)


@router.callback_query(F.data == "subscription_status")
async def status_callback(callback: CallbackQuery) -> None:
    """Статус подписки через inline-кнопку."""
    from bot.handlers import menu
    await menu.subscription_status(callback)


@router.callback_query(F.data == "vpn_profiles")
async def vpn_callback(callback: CallbackQuery) -> None:
    """VPN профили через inline-кнопку."""
    from bot.handlers import menu
    await menu.vpn_profiles(callback)


@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery) -> None:
    """Помощь через inline-кнопку."""
    from bot.keyboards.inline import get_help_keyboard
    text = (
        "📖 <b>Справка HutepVPN</b>\n\n"
        "🖥 <b>Мой кабинет</b> — информация о вашем аккаунте\n"
        "📊 <b>Статус подписки</b> — текущее состояние\n"
        "🔐 <b>VPN профили</b> — получить конфиг\n"
        "💳 <b>Оформить подписку</b> — купить подписку\n"
        "👥 <b>Рефералы</b> — пригласить друзей\n\n"
        "🎁 <b>Бонус:</b> +7 дней за каждого друга!\n\n"
        "💬 <b>Поддержка:</b> @HutepVPNSupport"
    )
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_help_keyboard(),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_help_keyboard(),
            parse_mode="HTML"
        )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Команда /help."""
    help_text = (
        "📖 <b>Справка по боту HutepVPN</b>\n\n"
        "🖥 <b>Мой кабинет</b> — информация о вашем аккаунте\n"
        "📊 <b>Статус подписки</b> — текущее состояние подписки\n"
        "🔐 <b>VPN профили</b> — получить или обновить VPN-конфиг\n"
        "💳 <b>Оформить подписку</b> — купить подписку\n"
        "👥 <b>Рефералы</b> — пригласить друзей и получить бонус\n"
        "📖 <b>Помощь</b> — эта справка\n\n"
        "🎁 <b>Реферальная программа:</b>\n"
        "Пригласите друга — оба получат <b>+7 дней</b> подписки!\n\n"
        "💬 Если нужна помощь — напишите @support"
    )

    await message.answer(help_text, parse_mode="HTML")
