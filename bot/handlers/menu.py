"""Хендлеры меню и профиля."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from bot.db.models import User, Subscription, get_session_maker
from bot.keyboards.inline import (
    get_profile_keyboard,
    get_help_keyboard,
    get_back_to_subscription_keyboard,
    get_vpn_profiles_keyboard,
)
from bot.utils.date_utils import format_date

router = Router(name="menu")


@router.callback_query(F.data == "cabinet")
async def my_cabinet(callback: CallbackQuery) -> None:
    """Личный кабинет пользователя."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await session.get(User, callback.from_user.id)
        if not user:
            try:
                await callback.message.answer("😕 Пользователь не найден.")
            except Exception:
                pass
            return

        subscription = await session.get(Subscription, user.id)
        has_subscription = subscription and subscription.is_valid

        from bot.services.referral_service import get_referral_service
        referral_svc = get_referral_service()
        referral_count = await referral_svc.get_referral_count(session, user.id)

        text = (
            f"🖥 <b>Личный кабинет</b>\n\n"
            f"👤 <b>Имя:</b> {user.full_name}\n"
            f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
            f"📅 <b>Регистрация:</b> {format_date(user.created_at)}\n"
            f"👥 <b>Рефералов:</b> {referral_count}\n\n"
        )

        if has_subscription:
            from bot.utils.date_utils import format_days_remaining
            from bot.utils.text_formatter import format_subscription_text
            text += format_subscription_text(subscription)
        else:
            text += "🚫 <b>Нет активной подписки</b>"

        try:
            await callback.message.edit_text(
                text,
                reply_markup=get_profile_keyboard(has_subscription),
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.answer(
                text,
                reply_markup=get_profile_keyboard(has_subscription),
                parse_mode="HTML"
            )


@router.callback_query(F.data == "subscription_status")
async def subscription_status(callback: CallbackQuery) -> None:
    """Просмотр статуса подписки."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        subscription = await session.get(Subscription, callback.from_user.id)

        if not subscription or not subscription.is_valid:
            text = (
                "🚫 <b>Нет активной подписки</b>\n\n"
                "💳 Оформите подписку для доступа к VPN-серверам!"
            )
        else:
            from bot.utils.text_formatter import format_subscription_text
            text = format_subscription_text(subscription)

        try:
            await callback.message.edit_text(
                text,
                reply_markup=get_back_to_subscription_keyboard(),
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.answer(
                text,
                reply_markup=get_back_to_subscription_keyboard(),
                parse_mode="HTML"
            )


@router.callback_query(F.data == "vpn_profiles")
async def vpn_profiles(callback: CallbackQuery) -> None:
    """Управление VPN профилями."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        user = await session.get(User, callback.from_user.id)
        if not user:
            try:
                await callback.message.answer("😕 Пользователь не найден.")
            except Exception:
                pass
            return

        subscription = await session.get(Subscription, user.id)

        if not subscription or not subscription.is_valid:
            text = (
                "🚫 <b>VPN недоступен</b>\n\n"
                "😔 Для получения VPN-профиля необходима активная подписка."
            )
            try:
                await callback.message.edit_text(
                    text,
                    reply_markup=get_back_to_subscription_keyboard(),
                    parse_mode="HTML"
                )
            except Exception:
                await callback.message.answer(
                    text,
                    reply_markup=get_back_to_subscription_keyboard(),
                    parse_mode="HTML"
                )
            return

        text = "🔐 <b>VPN профили</b>\n\n📱 Выберите действие:"
        try:
            await callback.message.edit_text(
                text,
                reply_markup=get_vpn_profiles_keyboard(),
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.answer(
                text,
                reply_markup=get_vpn_profiles_keyboard(),
                parse_mode="HTML"
            )


@router.callback_query(F.data == "vpn_show")
async def vpn_show_profile(callback: CallbackQuery) -> None:
    """Показать VPN профиль."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        from bot.db.models import VPNProfile
        from sqlalchemy import select
        from bot.config import settings

        subscription = await session.get(Subscription, callback.from_user.id)

        if not subscription or not subscription.is_valid:
            try:
                await callback.message.answer("😔 Сначала оформите подписку!")
            except Exception:
                pass
            return

        # Получаем или создаём VPN профиль
        from bot.services.vpn_service import get_vpn_service
        vpn_service = get_vpn_service()
        user_obj = await session.get(User, callback.from_user.id)
        profile = None
        if user_obj:
            try:
                profile = await vpn_service.get_or_create_profile(session, user_obj)
                await session.commit()
            except Exception as e:
                try:
                    await callback.message.answer(f"😔 Ошибка: {e}")
                except Exception:
                    pass
                return

        if profile and profile.profile_link:
            sub_url = profile.profile_link

            text = (
                "🔐 <b>Ваш VPN профиль</b>\n\n"
                f"⚙️ Протокол: <b>VLESS + Reality</b>\n"
                f"🖥 Сервер: <b>HutepVPN</b>\n"
                f"📋 Статус: <b>Активен ✅</b>\n\n"
                f"📱 <b>Ссылка для подключения:</b>\n"
                f"<code>{sub_url}</code>\n\n"
                "📋 <b>Инструкция для Android (Happ):</b>\n"
                "1️⃣ Установите <b>Happ</b> из Google Play\n"
                "2️⃣ Нажмите + → <b>Подписка (Subscription)</b>\n"
                "3️⃣ Вставьте ссылку выше\n"
                "4️⃣ Нажмите <b>ОК</b> и подключитесь\n\n"
                "⚠️ Ссылка действительна только при активной подписке!"
            )
            try:
                await callback.message.answer(text, parse_mode="HTML")
            except Exception:
                pass


@router.callback_query(F.data == "vpn_regenerate")
async def vpn_regenerate_profile(callback: CallbackQuery) -> None:
    """Пересоздание VPN профиля."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        from bot.db.models import VPNProfile
        from sqlalchemy import select

        subscription = await session.get(Subscription, callback.from_user.id)

        if not subscription or not subscription.is_valid:
            try:
                await callback.message.answer("😔 Сначала оформите подписку!")
            except Exception:
                pass
            return

        user_obj = await session.get(User, callback.from_user.id)
        if not user_obj:
            try:
                await callback.message.answer("😕 Пользователь не найден.")
            except Exception:
                pass
            return

        from bot.services.xui_service import get_xui_service
        from bot.services.vpn_service import VPNService, XUI_DEFAULT_INBOUND_ID
        import uuid

        xui = get_xui_service()
        try:
            client_data = await xui.create_client(
                email=str(user_obj.id),
                inbound_ids=[XUI_DEFAULT_INBOUND_ID],
            )
            if not client_data:
                raise Exception("X-UI returned no data")

            sub_id = client_data.get("subId", "")
            profile_link = xui.generate_subscription_url(str(sub_id))
        except Exception as e:
            text = f"😔 Ошибка при создании профиля в X-UI: {e}"
            try:
                await callback.message.answer(text, parse_mode="HTML")
            except Exception:
                pass
            return

        profile_uuid = client_data.get("id", str(uuid.uuid4()))
        profile = VPNProfile(
            user_id=user_obj.id,
            protocol="vless",
            profile_uuid=str(profile_uuid),
            sub_id=str(sub_id) if sub_id else None,
            profile_link=profile_link,
            server_name="HutepVPN Server",
            is_active=True,
        )
        session.add(profile)
        await session.commit()

        text = (
            "🔄 <b>VPN профиль обновлён!</b>\n\n"
            f"📋 <b>Новая ссылка:</b>\n"
            f"<code>{profile_link}</code>\n\n"
            "⚠️ Не забудьте обновить подписку в приложении!"
        )
        try:
            await callback.message.answer(text, parse_mode="HTML")
        except Exception:
            pass


@router.callback_query(F.data == "vpn_instructions")
async def vpn_instructions(callback: CallbackQuery) -> None:
    """Инструкция по подключению."""
    text = (
        "📖 <b>Инструкция по подключению (Android — Happ)</b>\n\n"
        "1️⃣ <b>Установите Happ:</b>\n"
        "• Скачайте из Google Play или f-droid\n\n"
        "2️⃣ <b>Добавьте подписку:</b>\n"
        "• Нажмите + на главном экране\n"
        "• Выберите <b>Подписка (Subscription)</b>\n"
        "• Вставьте вашу ссылку вида:\n"
        "<code>https://vpn.mylumina.ru:2096/sub/...</code>\n"
        "• Нажмите ОК\n\n"
        "3️⃣ <b>Подключитесь:</b>\n"
        "• Выберите добавленную подписку\n"
        "• Нажмите кнопку подключения (▶)\n\n"
        "4️⃣ <b>Разрешите VPN:</b>\n"
        "• При запросе нажмите ОК\n\n"
        "⚠️ <b>Важно:</b> Ссылка действительна только при активной подписке!\n"
        "💡 При проблемах напишите @HutepVPNSupport"
    )
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_vpn_profiles_keyboard(),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_vpn_profiles_keyboard(),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "help_servers")
async def help_servers(callback: CallbackQuery) -> None:
    """Статус серверов."""
    text = (
        "📡 <b>Статус серверов HutepVPN</b>\n\n"
        "🟢 <b>Все серверы онлайн</b>\n\n"
        "🔹 Сервер 1: онлайн\n"
        "🔹 Сервер 2: онлайн\n\n"
        "При проблемах со连接нием напишите @HutepVPNSupport"
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


@router.callback_query(F.data == "help_support")
async def help_support(callback: CallbackQuery) -> None:
    """Поддержка."""
    try:
        await callback.message.answer(
            "💬 <b>Свяжитесь с нами:</b>\n\n"
            "📱 Telegram: @HutepVPNSupport\n"
            "📧 Email: support@hutervpn.example.com",
            parse_mode="HTML"
        )
    except Exception:
        pass
