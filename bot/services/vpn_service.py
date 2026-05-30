"""Сервис управления VPN-профилями пользователей."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Subscription, User, VPNProfile
from bot.services.xui_service import get_xui_service, XUIServiceError

XUI_DEFAULT_INBOUND_ID = 1

logger = logging.getLogger(__name__)


class VPNServiceError(Exception):
    """Ошибка при работе с VPN сервисом."""
    pass


class VPNService:
    """Управление VPN-профилями пользователей."""

    def __init__(self) -> None:
        self.xui = get_xui_service()

    async def get_or_create_profile(
        self,
        session: AsyncSession,
        user: User,
        inbound_id: int = 1,
    ) -> VPNProfile:
        """
        Получить существующий профиль или создать новый.

        :param session: Сессия БД
        :param user: Пользователь
        :param inbound_id: ID входящего подключения в X-UI
        :return: VPN-профиль пользователя
        """
        stmt = select(VPNProfile).where(
            VPNProfile.user_id == user.id,
            VPNProfile.is_active == True,
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        try:
            client_data = await self.xui.create_client(
                email=str(user.id),
                inbound_ids=[XUI_DEFAULT_INBOUND_ID],
            )

            if not client_data:
                raise VPNServiceError("Failed to create client in X-UI")

            profile_uuid = client_data.get("id", str(uuid.uuid4()))
            sub_id = client_data.get("subId", "")
            profile_link = self.xui.generate_subscription_url(str(sub_id))

            profile = VPNProfile(
                user_id=user.id,
                protocol="vless",
                profile_uuid=str(profile_uuid),
                sub_id=str(sub_id) if sub_id else None,
                profile_link=profile_link,
                server_name="HutepVPN Server",
                is_active=True,
            )
            session.add(profile)
            await session.commit()
            await session.refresh(profile)

            return profile

        except XUIServiceError as e:
            logger.error(f"VPN profile creation error: {e}")
            raise VPNServiceError(f"X-UI API error: {e}")

    async def get_profile(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> VPNProfile | None:
        """Получение профиля пользователя."""
        stmt = select(VPNProfile).where(
            VPNProfile.user_id == user_id,
            VPNProfile.is_active == True,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_profile(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> bool:
        """Удаление профиля пользователя."""
        profile = await self.get_profile(session, user_id)
        if not profile:
            return False

        try:
            await self.xui.delete_client(str(user_id))
            profile.is_active = False
            await session.commit()
            return True
        except XUIServiceError:
            return False

    async def check_user_subscription(self, session: AsyncSession, user_id: int) -> Subscription | None:
        """Проверка подписки пользователя."""
        stmt = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.is_active == True,
        )
        result = await session.execute(stmt)
        subscription = result.scalar_one_or_none()

        if subscription and not subscription.is_valid:
            subscription.is_active = False
            await session.commit()

        return subscription


_vpn_service: VPNService | None = None


def get_vpn_service() -> VPNService:
    global _vpn_service
    if _vpn_service is None:
        _vpn_service = VPNService()
    return _vpn_service
