"""Хендлеры платежей (Telegram Stars и крипта)."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery

from bot.db.models import User, Subscription, Payment, get_session_maker
from bot.services.referral_service import get_referral_service
from bot.utils.date_utils import days_from_now

router = Router(name="payment")


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    """Обработка pre-checkout запроса (подтверждение перед оплатой Stars)."""
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message) -> None:
    """Обработка успешного платежа через Telegram Stars."""
    payment = message.successful_payment

    payload = payment.payload
    parts = payload.split("_")

    if len(parts) < 2:
        await message.answer("😔 Ошибка обработки платежа. Обратитесь в поддержку.")
        return

    days = int(parts[1])

    session_maker = get_session_maker()
    async with session_maker() as session:
        # Обновляем статус платежа
        from sqlalchemy import select
        stmt = select(Payment).where(Payment.user_id == message.from_user.id)
        stmt = stmt.order_by(Payment.created_at.desc())
        result = await session.execute(stmt)
        payment_record = result.scalar_one_or_none()

        if payment_record:
            payment_record.status = "completed"
            await session.commit()

        # Активируем подписку
        await _activate_subscription(message.from_user.id, days)

        # Применяем реферальный бонус
        user = await session.get(User, message.from_user.id)
        if user and user.referred_by:
            referral_svc = get_referral_service()
            await referral_svc.apply_referral_bonus(session, user)

    await message.answer(
        "🎉 <b>Оплата прошла успешно!</b>\n\n"
        f"✅ Подписка активирована на <b>{days} дней</b>\n\n"
        "🔐 Теперь вы можете получить VPN-профиль в разделе «🔐 VPN профили»\n\n"
        "💡 <b>Не забудьте:</b> Приглашайте друзей и получайте +7 дней бесплатно!",
        parse_mode="HTML"
    )


async def _activate_subscription(user_id: int, days: int) -> Subscription:
    """Активация или продление подписки пользователя."""
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