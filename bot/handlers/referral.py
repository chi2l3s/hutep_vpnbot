"""Хендлеры реферальной системы."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from bot.db.models import User, get_session_maker
from bot.keyboards.inline import get_referral_keyboard, get_main_menu_inline_keyboard
from bot.services.referral_service import get_referral_service

router = Router(name="referral")


@router.message(F.text == "👥 Рефералы")
@router.message(Command("referral"))
async def referral_info_message(message: Message) -> None:
    """Информация о реферальной программе (через сообщение)."""
    user_id = message.from_user.id

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.reply("😕 Пользователь не найден.")
            return

        referral_svc = get_referral_service()
        referral_count = await referral_svc.get_referral_count(session, user_id)
        referral_list = await referral_svc.get_referral_list(session, user_id)

        bot_me = await message.bot.me()
        referral_link = referral_svc.generate_referral_link(bot_me.username, user.referral_code)

        text = (
            "👥 <b>Реферальная программа</b>\n\n"
            f"📊 Приглашений: <b>{referral_count}</b>\n\n"
            f"🎁 <b>Бонус:</b> +7 дней подписки каждому!\n\n"
            f"🔗 <b>Ваш реферальный код:</b>\n"
            f"<code>{user.referral_code}</code>\n\n"
            f"🔗 <b>Ссылка для приглашения:</b>\n"
            f"{referral_link}\n\n"
            "📨 <b>Как это работает:</b>\n"
            "1️⃣ Отправьте ссылку другу\n"
            "2️⃣ Друг перейдёт по ссылке и купит подписку\n"
            "3️⃣ Вы оба получите +7 дней бесплатно!"
        )

        if referral_count > 0:
            text += "\n\n📋 <b>Ваши рефералы:</b>"
            for i, ref in enumerate(referral_list[:5], 1):
                text += f"\n{i}. {ref.full_name} ({ref.created_at.strftime('%d.%m.%Y')})"

        await message.answer(text, reply_markup=get_referral_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "referral_info")
async def referral_info_callback(callback: CallbackQuery) -> None:
    """Информация о реферальной программе (через callback)."""
    user_id = callback.from_user.id

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await session.get(User, user_id)
        if not user:
            try:
                await callback.message.answer("😕 Пользователь не найден.")
            except Exception:
                pass
            return

        referral_svc = get_referral_service()
        referral_count = await referral_svc.get_referral_count(session, user_id)
        referral_list = await referral_svc.get_referral_list(session, user_id)

        bot_me = await callback.bot.me()
        referral_link = referral_svc.generate_referral_link(bot_me.username, user.referral_code)

        text = (
            "👥 <b>Реферальная программа</b>\n\n"
            f"📊 Приглашений: <b>{referral_count}</b>\n\n"
            f"🎁 <b>Бонус:</b> +7 дней подписки каждому!\n\n"
            f"🔗 <b>Ваш реферальный код:</b>\n"
            f"<code>{user.referral_code}</code>\n\n"
            f"🔗 <b>Ссылка для приглашения:</b>\n"
            f"{referral_link}\n\n"
            "📨 <b>Как это работает:</b>\n"
            "1️⃣ Отправьте ссылку другу\n"
            "2️⃣ Друг перейдёт по ссылке и купит подписку\n"
            "3️⃣ Вы оба получите +7 дней бесплатно!"
        )

        if referral_count > 0:
            text += "\n\n📋 <b>Ваши рефералы:</b>"
            for i, ref in enumerate(referral_list[:5], 1):
                text += f"\n{i}. {ref.full_name} ({ref.created_at.strftime('%d.%m.%Y')})"

        try:
            await callback.message.edit_text(
                text,
                reply_markup=get_referral_keyboard(),
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.answer(
                text,
                reply_markup=get_referral_keyboard(),
                parse_mode="HTML"
            )


@router.callback_query(F.data == "referral_help")
async def referral_help(callback: CallbackQuery) -> None:
    """Информация о правилах реферальной программы."""
    text = (
        "📖 <b>Как работает реферальная программа?</b>\n\n"
        "🎁 <b>Что вы получаете:</b>\n"
        "• +7 дней к вашей подписке за каждого реферала\n"
        "• Реферал тоже получает +7 дней!\n\n"
        "📨 <b>Как пригласить:</b>\n"
        "1️⃣ Нажмите «👥 Рефералы» в меню\n"
        "2️⃣ Скопируйте вашу ссылку или код\n"
        "3️⃣ Отправьте другу\n\n"
        "⚠️ <b>Условия:</b>\n"
        "• Бонус начисляется только при первой покупке реферала\n"
        "• Минимальная сумма покупки: 70₽\n"
        "• Бонусные дни добавляются к активной подписке"
    )
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_referral_keyboard(),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_referral_keyboard(),
            parse_mode="HTML"
        )
