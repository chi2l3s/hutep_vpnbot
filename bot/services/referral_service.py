"""Сервис реферальной системы."""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.models import Subscription, User
from bot.utils.date_utils import days_from_now, extend_subscription

logger = logging.getLogger(__name__)


class ReferralService:
    """Управление реферальной системой."""

    @staticmethod
    async def get_user_by_referral_code(
        session: AsyncSession,
        code: str,
    ) -> User | None:
        """Поиск пользователя по реферальному коду."""
        stmt = select(User).where(User.referral_code == code)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_referral_count(session: AsyncSession, user_id: int) -> int:
        """Получение количества рефералов пользователя."""
        stmt = select(User).where(User.referred_by == user_id)
        result = await session.execute(stmt)
        return len(result.scalars().all())

    @staticmethod
    async def apply_referral_bonus(session: AsyncSession, user: User) -> bool:
        """
        Начисление бонуса за покупку реферала.

        Когда реферал покупает подписку:
        1. Реферал получает +7 дней к своей подписке
        2. Реферер получает +7 дней к своей подписке
        """
        bonus_days = settings.referral_bonus_days
        if bonus_days <= 0:
            return False

        try:
            # 1. Бонус покупателю (рефералу)
            await ReferralService._add_bonus_to_subscription(
                session=session,
                user_id=user.id,
                bonus_days=bonus_days,
            )

            # 2. Бонус рефереру
            if user.referred_by:
                referrer = await session.get(User, user.referred_by)
                if referrer:
                    await ReferralService._add_bonus_to_subscription(
                        session=session,
                        user_id=referrer.id,
                        bonus_days=bonus_days,
                    )
                    logger.info(f"Referral bonus applied: {bonus_days} days to user {referrer.id}")

            await session.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to apply referral bonus: {e}")
            await session.rollback()
            return False

    @staticmethod
    async def _add_bonus_to_subscription(
        session: AsyncSession,
        user_id: int,
        bonus_days: int,
    ) -> None:
        """Добавление бонусных дней к подписке."""
        stmt = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.is_active == True,
        )
        result = await session.execute(stmt)
        subscription = result.scalar_one_or_none()

        if subscription:
            # Продлеваем существующую подписку
            new_end = extend_subscription(subscription.end_date, bonus_days)
            subscription.end_date = new_end
            subscription.days += bonus_days
        else:
            # Если подписки нет — создаём бонусную запись
            # (на случай, если реферал купил в первый раз без подписки)
            new_subscription = Subscription(
                user_id=user_id,
                days=bonus_days,
                start_date=datetime.utcnow(),
                end_date=days_from_now(bonus_days),
                is_active=True,
            )
            session.add(new_subscription)

    @staticmethod
    async def get_referral_list(session: AsyncSession, user_id: int) -> list[User]:
        """Получение списка рефералов пользователя."""
        stmt = select(User).where(User.referred_by == user_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def generate_referral_link(bot_username: str, code: str) -> str:
        """Генерация реферальной ссылки."""
        return f"https://t.me/{bot_username}?start={code}"


# Глобальный экземпляр
_referral_service: ReferralService | None = None


def get_referral_service() -> ReferralService:
    """Получение экземпляра сервиса рефералов."""
    global _referral_service
    if _referral_service is None:
        _referral_service = ReferralService()
    return _referral_service