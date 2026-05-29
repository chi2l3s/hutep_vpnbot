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

    def _get_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    result = await response.json()

                    if response.status >= 400:
                        logger.error(f"X-UI API error {response.status}: {result}")
                        raise XUIServiceError(f"API error {response.status}")

                    return result

        except aiohttp.ClientError as e:
            logger.error(f"X-UI connection error: {e}")
            raise XUIServiceError(f"Connection error: {e}")

    # ─── Inbounds ───────────────────────────────────────────

    async def get_inbounds(self) -> list[dict[str, Any]]:
        """Список всех inbounds."""
        try:
            result = await self._request("GET", "/inbounds/list")
            return result.get("obj", [])
        except XUIServiceError as e:
            logger.error(f"Failed to get inbounds: {e}")
            return []

    async def get_inbounds_options(self) -> list[dict[str, Any]]:
        """Краткий список inbounds (id, remark, port, protocol)."""
        try:
            result = await self._request("GET", "/inbounds/options")
            return result.get("obj", [])
        except XUIServiceError:
            return []

    # ─── Clients ───────────────────────────────────────────

    async def get_clients(self) -> list[dict[str, Any]]:
        """Все клиенты с uuid, subId, traffic."""
        try:
            result = await self._request("GET", "/clients/list")
            return result.get("obj", [])
        except XUIServiceError as e:
            logger.error(f"Failed to get clients: {e}")
            return []

    async def get_client_paged(
        self,
        page: int = 1,
        page_size: int = 25,
        search: str | None = None,
    ) -> dict[str, Any]:
        """Клиенты с пагинацией и поиском."""
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        if search:
            params["search"] = search
        try:
            return await self._request("GET", "/clients/list/paged", params=params)
        except XUIServiceError as e:
            logger.error(f"Failed to get paged clients: {e}")
            return {"obj": {"items": [], "total": 0, "filtered": 0}}

    async def get_client(self, email: str) -> dict[str, Any] | None:
        """Получить клиента по email (= subId = telegram_id)."""
        try:
            result = await self._request("GET", f"/clients/get/{email}")
            return result.get("obj")
        except XUIServiceError:
            return None

    async def create_client(
        self,
        email: str,
        inbound_ids: list[int],
        tg_id: int = 0,
        expiry_time: int = 0,
        total_gb: int = 0,
    ) -> dict[str, Any] | None:
        """Создать клиента.

        POST /panel/api/clients/add
        Body: {client: {email, tgId, expiryTime, totalGB, enable: true}, inboundIds: [id]}
        """
        body = {
            "client": {
                "email": email,
                "tgId": tg_id,
                "expiryTime": expiry_time,
                "totalGB": total_gb,
                "enable": True,
            },
            "inboundIds": inbound_ids,
        }
        try:
            result = await self._request("POST", "/clients/add", data=body)
            if not result.get("success"):
                logger.error(f"Create client failed: {result}")
                return None
            return result.get("obj")
        except XUIServiceError as e:
            logger.error(f"Failed to create client: {e}")
            return None

    async def update_client(
        self,
        email: str,
        expiry_time: int | None = None,
        total_gb: int | None = None,
        enable: bool | None = None,
        tg_id: int | None = None,
    ) -> bool:
        """Обновить клиента. POST /clients/update/:email."""
        body: dict[str, Any] = {"email": email}
        if expiry_time is not None:
            body["expiryTime"] = expiry_time
        if total_gb is not None:
            body["totalGB"] = total_gb
        if enable is not None:
            body["enable"] = enable
        if tg_id is not None:
            body["tgId"] = tg_id
        try:
            result = await self._request("POST", f"/clients/update/{email}", data=body)
            return result.get("success", False)
        except XUIServiceError:
            return False

    async def delete_client(self, email: str) -> bool:
        """Удалить клиента. POST /clients/del/:email."""
        try:
            result = await self._request("POST", f"/clients/del/{email}")
            return result.get("success", False)
        except XUIServiceError:
            return False

    async def get_client_traffic(self, email: str) -> dict[str, Any] | None:
        """Трафик клиента. GET /clients/traffic/:email."""
        try:
            result = await self._request("GET", f"/clients/traffic/{email}")
            return result.get("obj")
        except XUIServiceError:
            return None

    async def reset_client_traffic(self, email: str) -> bool:
        """Сбросить трафик клиента. POST /clients/resetTraffic/:email."""
        try:
            result = await self._request("POST", f"/clients/resetTraffic/{email}")
            return result.get("success", False)
        except XUIServiceError:
            return False

    # ─── Subscription ─────────────────────────────────

    def generate_subscription_url(self, sub_id: str) -> str:
        """Subscription URL: https://vpn.mylumina.ru:2096/sub/{sub_id}"""
        return f"{settings.xui_sub_base_url}{settings.xui_sub_path}{sub_id}"

    # ─── Прочее ─────────────────────────────────────────

    async def get_online_clients(self) -> list[str]:
        """Список email клиентов онлайн. POST /clients/onlines."""
        try:
            result = await self._request("POST", "/clients/onlines")
            return result.get("obj", [])
        except XUIServiceError:
            return []

    async def check_connection(self) -> bool:
        """Проверка соединения с X-UI API."""
        try:
            await self.get_inbounds()
            return True
        except Exception:
            return False


_xui_service: XUIService | None = None


def get_xui_service() -> XUIService:
    """Получить экземпляр X-UI сервиса."""
    global _xui_service
    if _xui_service is None:
        _xui_service = XUIService()
    return _xui_service
