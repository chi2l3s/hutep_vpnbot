"""Сервис для работы с X-UI панелью."""

import logging
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

    async def get_inbound_info(self, inbound_id: int = 1) -> dict[str, Any] | None:
        """Получение информации о входящем подключении."""
        try:
            result = await self._request("GET", f"/xui/inbounds/{inbound_id}")
            return result.get("obj")
        except XUIServiceError:
            return None

    async def create_client(
        self,
        email: str,
        inbound_id: int = 1,
        enable: bool = True,
        flow: str = "xtls-rprx-vision",
    ) -> dict[str, Any] | None:
        """
        Создание нового VPN-клиента.

        :param email: Email/идентификатор клиента (используем Telegram ID)
        :param inbound_id: ID входящего подключения
        :param enable: Включить ли клиента
        :param flow: Тип протокола (VLESS)
        :return: Данные созданного клиента
        """
        client_data = {
            "enable": enable,
            "email": email,
            "flow": flow,
            "limitIp": 0,
            "totalGB": 0,
            "expiryTime": 0,
            "listen": "",
            "protocol": "vless",
            "settings": '{"clients": []}',
        }

        try:
            result = await self._request(
                "POST",
                f"/xui/inbounds/{inbound_id}/clients",
                data=client_data,
            )
            return result.get("obj")
        except XUIServiceError as e:
            logger.error(f"Failed to create client: {e}")
            return None

    async def get_clients(self, inbound_id: int = 1) -> list[dict[str, Any]]:
        """Получение списка клиентов для входящего подключения."""
        try:
            inbound = await self.get_inbound_info(inbound_id)
            if inbound:
                settings_data = inbound.get("settings", "{}")
                import json
                settings = json.loads(settings_data)
                return settings.get("clients", [])
            return []
        except Exception:
            return []

    async def delete_client(self, email: str, inbound_id: int = 1) -> bool:
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

    async def find_client(self, email: str, inbound_id: int = 1) -> dict[str, Any] | None:
        """Поиск клиента по email (Telegram ID)."""
        clients = await self.get_clients(inbound_id)
        for client in clients:
            if client.get("email") == str(email):
                return client
        return None

    async def generate_vless_link(
        self,
        client_uuid: str,
        server_host: str,
        server_port: int,
        flow: str = "xtls-rprx-vision",
    ) -> str:
        """
        Генерация VLESS-ссылки для подключения.

        :param client_uuid: UUID клиента
        :param server_host: Хост сервера
        :param server_port: Порт сервера
        :param flow: Тип потока
        :return: VLESS-ссылка
        """
        return f"vless://{client_uuid}@{server_host}:{server_port}?flow={flow}#{server_host}"

    async def get_or_create_client(self, telegram_id: int) -> dict[str, Any] | None:
        """
        Получить существующего клиента или создать нового.

        :param telegram_id: Telegram ID пользователя
        :return: Данные клиента или None
        """
        email = str(telegram_id)

        # Проверяем, существует ли клиент
        existing = await self.find_client(email)
        if existing:
            return existing

        # Создаём нового клиента
        return await self.create_client(email)

    async def check_connection(self) -> bool:
        """Проверка соединения с X-UI API."""
        try:
            inbounds = await self.get_inbounds()
            return True
        except Exception:
            return False


# Глобальный экземпляр сервиса
_xui_service: XUIService | None = None


def get_xui_service() -> XUIService:
    """Получение экземпляра X-UI сервиса."""
    global _xui_service
    if _xui_service is None:
        _xui_service = XUIService()
    return _xui_service