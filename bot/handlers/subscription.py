"""Хендлеры оформления подписки."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, LabeledPrice
from aiogram.methods import SendInvoice
from aiogram.fsm.context import FSMContext

from bot.db.models import Subscription, Payment, get_session_maker
from bot.config import settings
from bot.keyboards.inline import (
    get_subscription_plans_keyboard,
    get_payment_methods_keyboard,
    get_back_to_subscription_keyboard,
)
from bot.utils.date_utils import days_from_now

router = Router(name="subscription")


@router.callback_query(F.data == "subscribe")
@router.message(F.text == "/subscribe")
async def subscribe(callback_or_message, state: FSMContext | None = None) -> None:
    """Показать выбор тарифного плана."""
    is_callback = isinstance(callback_or_message, CallbackQuery)

    plans_text = (
        "💳 <b>Выберите подписку</b>\n\n"
        "🛡 Единая подписка даёт доступ ко всем VPN-серверам!\n\n"
        "📊 <b>Доступные тарифы:</b>\n\n"
    )

    for days, plan in settings.subscription_plans.items():
        price = plan["price"]
        name = plan["name"]

        badges = {30: "📌", 90: "🔥", 180: "⭐", 360: "👑"}
        badge = badges.get(days, "📌")
        price_per_day = price / days

        plans_text += (
            f"{badge} <b>{name}</b>\n"
            f"   💰 Цена: <b>{price}₽</b>\n"
            f"   📅 Срок: <b>{days} дней</b>\n"
            f"   💵 Цена/день: <b>{price_per_day:.2f}₽</b>\n\n"
        )

    plans_text += (
        "💡 <b>Совет:</b> Чем больше срок — тем выгоднее!\n"
        "🎁 Бонус за рефералов: <b>+7 дней</b> бесплатно!"
    )

    try:
        if is_callback:
            await callback_or_message.message.edit_text(
                plans_text,
                reply_markup=get_subscription_plans_keyboard(),
                parse_mode="HTML"
            )
        else:
            await callback_or_message.answer(
                plans_text,
                reply_markup=get_subscription_plans_keyboard(),
                parse_mode="HTML"
            )
    except Exception:
        await callback_or_message.message.answer(
            plans_text,
            reply_markup=get_subscription_plans_keyboard(),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("sub_select_"))
async def select_plan(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор конкретного тарифного плана."""
    days = int(callback.data.replace("sub_select_", ""))
    plan = settings.subscription_plans.get(days)
    if not plan:
        try:
            await callback.message.answer("❌ Неверный тариф")
        except Exception:
            pass
        return

    await state.update_data(selected_days=days, selected_price=plan["price"])

    text = (
        "🔍 <b>Вы выбрали:</b>\n\n"
        f"📦 <b>{plan['name']}</b>\n"
        f"💰 Цена: <b>{plan['price']}₽</b>\n"
        f"📅 Срок: <b>{days} дней</b>\n\n"
        "💳 <b>Выберите способ оплаты:</b>"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_payment_methods_keyboard(days),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_payment_methods_keyboard(days),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("pay_stars_"))
async def pay_with_stars(callback: CallbackQuery, state: FSMContext) -> None:
    """Инициация оплаты через Telegram Stars."""
    days = int(callback.data.replace("pay_stars_", ""))
    plan = settings.subscription_plans.get(days)
    if not plan:
        try:
            await callback.message.answer("❌ Неверный тариф")
        except Exception:
            pass
        return

    price = plan["price"]
    # 1₽ = 0.8 Stars → Stars = price × 0.8
    stars_amount = max(1, int(price * 0.8))

    session_maker = get_session_maker()
    async with session_maker() as session:
        payment = Payment(
            user_id=callback.from_user.id,
            amount=float(price),
            amount_stars=stars_amount,
            days=days,
            status="pending",
            payment_method="stars",
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)

        try:
            await callback.bot(
                SendInvoice(
                    chat_id=callback.from_user.id,
                    title=f"HutepVPN — {days} дней",
                    description=f"Подписка на VPN-сервис HutepVPN на {days} дней",
                    payload=f"sub_{days}_{payment.id}",
                    provider_token="XTR",
                    currency="XTR",
                    prices=[LabeledPrice(label=f"Подписка {days} дней", amount=stars_amount)],
                )
            )
        except Exception as e:
            try:
                await callback.message.answer(
                    f"😔 Ошибка при создании счёта.\n\nПодробности: {e}",
                    parse_mode="HTML"
                )
            except Exception:
                pass


@router.callback_query(F.data.startswith("pay_crypto_"))
async def pay_with_crypto(callback: CallbackQuery, state: FSMContext) -> None:
    """Инициация оплаты через криптовалюту."""
    days = int(callback.data.replace("pay_crypto_", ""))
    plan = settings.subscription_plans.get(days)
    if not plan:
        try:
            await callback.message.answer("❌ Неверный тариф")
        except Exception:
            pass
        return

    price = plan["price"]

    from bot.services.payment_service import get_payment_service
    payment_svc = get_payment_service()
    result = await payment_svc.create_crypto_invoice(
        amount=float(price),
        days=days,
        user_telegram_id=callback.from_user.id,
    )

    if not result.success:
        try:
            await callback.message.answer(
                f"😔 Ошибка при создании счёта: {result.error}",
                parse_mode="HTML"
            )
        except Exception:
            pass
        return

    session_maker = get_session_maker()
    async with session_maker() as session:
        payment = Payment(
            user_id=callback.from_user.id,
            amount=float(price),
            days=days,
            status="pending",
            payment_method="crypto",
            invoice_id=result.invoice_id,
            crypto_address=result.crypto_address,
            crypto_amount=result.crypto_amount,
        )
        session.add(payment)
        await session.commit()

    text = (
        "₿ <b>Оплата криптовалютой</b>\n\n"
        f"💰 Сумма: <b>{price}₽</b>\n"
        f"📦 Подписка: <b>{days} дней</b>\n\n"
        f"🔗 <b>Ссылка для оплаты:</b>\n"
        f"{result.payment_url or 'Ссылка недоступна'}\n\n"
        "⏳ После оплаты нажмите «Проверить оплату»"
    )

    try:
        await callback.message.answer(
            text,
            reply_markup=get_back_to_subscription_keyboard(),
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment(callback: CallbackQuery) -> None:
    """Проверка статуса крипто-платежа."""
    invoice_id = callback.data.replace("check_payment_", "")
    session_maker = get_session_maker()

    async with session_maker() as session:
        from sqlalchemy import select
        stmt = select(Payment).where(Payment.invoice_id == invoice_id)
        result = await session.execute(stmt)
        payment = result.scalar_one_or_none()

        if not payment:
            try:
                await callback.message.answer("❌ Платёж не найден")
            except Exception:
                pass
            return

        if payment.status == "completed":
            try:
                await callback.message.answer("✅ Платёж уже обработан!")
            except Exception:
                pass
            return

        payment_days = payment.days
        payment_id = payment.id

    from bot.services.payment_service import get_payment_service
    payment_svc = get_payment_service()
    check_result = await payment_svc.check_crypto_payment(invoice_id)

    if check_result.is_paid:
        await _activate_subscription(callback.from_user.id, payment_days)

        async with session_maker() as session:
            from sqlalchemy import select
            stmt = select(Payment).where(Payment.id == payment_id)
            result = await session.execute(stmt)
            payment = result.scalar_one_or_none()
            if payment:
                payment.status = "completed"
                await session.commit()

        try:
            await callback.message.answer(
                f"🎉 <b>Оплата подтверждена!</b>\n\n"
                f"✅ Подписка активирована на <b>{payment_days} дней</b>!",
                parse_mode="HTML"
            )
        except Exception:
            pass
    else:
        try:
            await callback.message.answer(
                "⏳ <b>Платёж ещё не подтверждён.</b>\n\n"
                "Подождите несколько минут и попробуйте снова.\n"
                "Криптовалютные платежи обрабатываются 1-10 мин.",
                parse_mode="HTML"
            )
        except Exception:
            pass


async def _activate_subscription(user_id: int, days: int) -> Subscription:
    """Активация или продление подписки."""
    from datetime import datetime
    from sqlalchemy import select
    from bot.utils.date_utils import extend_subscription

    session_maker = get_session_maker()
    async with session_maker() as session:
        stmt = select(Subscription).where(Subscription.user_id == user_id)
        result = await session.execute(stmt)
        subscription = result.scalar_one_or_none()

        now = datetime.utcnow()

        if subscription and subscription.is_valid:
            subscription.end_date = extend_subscription(subscription.end_date, days)
            subscription.days += days
        else:
            subscription = Subscription(
                user_id=user_id,
                days=days,
                start_date=now,
                end_date=days_from_now(days),
                is_active=True,
            )
            session.add(subscription)

        await session.commit()
        await session.refresh(subscription)
        return subscription
