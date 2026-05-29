"""Сервис для работы с X-UI панелью."""

import json
import logging
import uuid
from typing import Any

import aiohttp

from bot.config import settings

logger = logging.getLogger(__name__)


class XUIServiceError(Exception):
    """Ошибка при работе с X-UI API."""
    pass


class XUIService:
    """Клиент для взаимодействия с X-UI API."""

    def __init__(self) -> None:
        self.base_url = settings.xui_api_url.rstrip("/")
        self.api_key = settings.xui_api_key
        self.use_tls = settings.xui_use_tls

    def _get_headers(self) -> dict:
        """Заголовки для запросов к API."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    async def _request(self, method: str, endpoint: str, data: dict | None = None) -> dict[str, Any]:
        """Выполнение HTTP-запроса к X-UI API."""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    json=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    result = await response.json()

                    if response.status >= 400:
                        logger.error(f"X-UI API error: {response.status} - {result}")
                        raise XUIServiceError(f"API error: {response.status}")

                    return result

        except aiohttp.ClientError as e:
            logger.error(f"X-UI connection error: {e}")
            raise XUIServiceError(f"Connection error: {e}")

    async def get_inbounds(self) -> list[dict[str, Any]]:
        """Получение списка входящих подключений (inbounds)."""
        try:
            result = await self._request("GET", "/xui/inbounds")
            return result.get("obj", [])
        except XUIServiceError as e:
            logger.error(f"Failed to get inbounds: {e}")
            return []

    async def get_inbound_info(self, inbound_id: int) -> dict[str, Any] | None:
        """Получение информации о входящем подключении."""
        try:
            result = await self._request("GET", f"/xui/inbounds/{inbound_id}")
            return result.get("obj")
        except XUIServiceError:
            return None

    async def create_client(
        self,
        email: str,
        inbound_id: int,
        tg_id: int | None = None,
        enable: bool = True,
        flow: str = "xtls-rprx-vision",
        expiry_time: int = 0,
        total_gb: int = 0,
    ) -> dict[str, Any] | None:
        """Создание нового VPN-клиента в X-UI.

        API: POST /xui/inbounds/{id}/clients
        Body: email, id (uuid), tgId, enable, flow, totalGB, expiryTime, inboundIds
        """
        client_uuid = str(uuid.uuid4())
        client_data = {
            "email": email,
            "id": client_uuid,
            "tgId": tg_id or 0,
            "enable": enable,
            "flow": flow,
            "totalGB": total_gb,
            "expiryTime": expiry_time,
            "subId": email,
        }
        try:
            result = await self._request(
                "POST",
                f"/xui/inbounds/{inbound_id}/clients",
                data={"id": client_uuid, "email": email, "tgId": tg_id or 0,
                      "enable": enable, "flow": flow, "totalGB": total_gb,
                      "expiryTime": expiry_time, "subId": email, "inboundIds": [inbound_id]},
            )
            return result.get("obj")
        except XUIServiceError as e:
            logger.error(f"Failed to create client: {e}")
            return None

    async def get_client_by_email(self, email: str, inbound_id: int) -> dict[str, Any] | None:
        """Поиск клиента по email в inbound."""
        try:
            inbound = await self.get_inbound_info(inbound_id)
            if inbound:
                settings_data = inbound.get("settings", "{}")
                s = json.loads(settings_data) if isinstance(settings_data, str) else settings_data
                for client in s.get("clients", []):
                    if client.get("email") == email:
                        return client
            return None
        except Exception:
            return None

    async def find_client(self, email: str, inbound_id: int) -> dict[str, Any] | None:
        """Поиск клиента по email."""
        return await self.get_client_by_email(email, inbound_id)

    async def delete_client(self, email: str, inbound_id: int) -> bool:
        """Удаление клиента по email."""
        try:
            await self._request(
                "DELETE",
                f"/xui/inbounds/{inbound_id}/clients",
                data={"email": email}
            )
            return True
        except XUIServiceError:
            return False

    def generate_subscription_url(self, sub_id: str) -> str:
        """Генерация subscription URL."""
        return f"{settings.subscription_domain}/sub/{sub_id}"

    async def get_or_create_client(
        self,
        telegram_id: int,
        inbound_id: int = 1,
        expiry_time: int = 0,
    ) -> dict[str, Any] | None:
        """Получить существующего клиента или создать нового."""
        email = str(telegram_id)

        existing = await self.find_client(email, inbound_id)
        if existing:
            return existing

        return await self.create_client(
            email=email,
            inbound_id=inbound_id,
            tg_id=telegram_id,
            expiry_time=expiry_time,
        )

    async def check_connection(self) -> bool:
        """Проверка соединения с X-UI API."""
        try:
            await self.get_inbounds()
            return True
        except Exception:
            return False


_xui_service: XUIService | None = None


def get_xui_service() -> XUIService:
    """Получение экземпляра X-UI сервиса."""
    global _xui_service
    if _xui_service is None:
        _xui_service = XUIService()
    return _xui_service
