"""Сервис для работы с 3X-UI панелью."""

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
    """Клиент для взаимодействия с 3X-UI Panel API."""

    def __init__(self) -> None:
        # XUI_API_URL из .env содержит полный путь:
        # https://vpn.mylumina.ru:48291/cPQ3oKGCuGtngvqGOx/panel/api
        raw = settings.xui_api_url.rstrip("/")
        if "/panel/api" in raw:
            self.base_url = raw[: raw.index("/panel/api")]
            self.path_prefix = raw[raw.index("/panel/api") + len("/panel/api") :]
        else:
            self.base_url = raw
            self.path_prefix = ""

        self.api_key = settings.xui_api_key
        # X-UI — свой сервер, прокси не нужен
        self.proxy = None

    def _url(self, endpoint: str) -> str:
        """Полный URL: https://host/path_prefix/panel/api/endpoint"""
        return f"{self.base_url}{self.path_prefix}/panel/api{endpoint}"

    def _headers(self) -> dict:
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
        url = self._url(endpoint)
        headers = self._headers()

        try:
            async with aiohttp.ClientSession(trust_env=False) as session:
                async with session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=headers,
                    proxy=self.proxy,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 404:
                        logger.warning(f"X-UI endpoint not found (404): {url}")
                        raise XUIServiceError(f"Endpoint not found: {url}")

                    if response.status >= 400:
                        text = await response.text()
                        logger.error(f"X-UI API error {response.status}: {text[:300]}")
                        raise XUIServiceError(f"API error {response.status}")

                    result = await response.json()
                    return result

        except aiohttp.ClientError as e:
            logger.error(f"X-UI connection error: {e}")
            raise XUIServiceError(f"Connection error: {e}")

    # ─── Inbounds ───────────────────────────────────────────────

    async def get_inbounds(self) -> list[dict[str, Any]]:
        """Список всех inbounds с клиентами. GET /inbounds/list."""
        try:
            result = await self._request("GET", "/inbounds/list")
            return result.get("obj", []) if result.get("success") else []
        except XUIServiceError as e:
            logger.error(f"Failed to get inbounds: {e}")
            return []

    async def get_inbounds_options(self) -> list[dict[str, Any]]:
        """Краткий список inbounds (id, remark, protocol, port).
        GET /inbounds/options."""
        try:
            result = await self._request("GET", "/inbounds/options")
            return result.get("obj", []) if result.get("success") else []
        except XUIServiceError as e:
            logger.error(f"Failed to get inbounds options: {e}")
            return []

    async def get_inbound(self, inbound_id: int) -> dict[str, Any] | None:
        """Один inbound по ID. GET /inbounds/get/{id}."""
        try:
            result = await self._request("GET", f"/inbounds/get/{inbound_id}")
            return result.get("obj") if result.get("success") else None
        except XUIServiceError:
            return None

    async def update_inbound(self, inbound_id: int, payload: dict[str, Any]) -> bool:
        """Обновить inbound полностью. POST /inbounds/update/{id}."""
        try:
            result = await self._request("POST", f"/inbounds/update/{inbound_id}", data=payload)
            return result.get("success", False)
        except XUIServiceError:
            return False

    # ─── Clients (через inbound settings) ───────────────────────

    def _client_by_email(self, inbound: dict, email: str) -> dict | None:
        """Найти клиента внутри inbound.settings.clients по email/tgId."""
        clients: list[dict] = inbound.get("settings", {}).get("clients", [])
        for c in clients:
            if c.get("email") == email or str(c.get("tgId")) == email:
                return c
        return None

    async def get_client(self, email: str) -> dict | None:
        """Найти клиента по email/tgId. Ищем во всех inbounds."""
        inbounds = await self.get_inbounds()
        for ib in inbounds:
            c = self._client_by_email(ib, email)
            if c:
                return {
                    **c,
                    "inbound_id": ib.get("id"),
                    "protocol": ib.get("protocol"),
                    "port": ib.get("port"),
                }
        return None

    async def create_client(
        self,
        email: str,
        inbound_ids: list[int],
        tg_id: int = 0,
        expiry_time: int = 0,
        total_gb: int = 0,
    ) -> dict | None:
        """Создать клиента. Для каждого inbound_id:
           1. GET /inbounds/get/{id} — получить текущий inbound
           2. Добавить клиента в settings.clients
           3. POST /inbounds/update/{id} — сохранить
        """
        new_client = {
            "id": str(uuid.uuid4()),
            "email": email,
            "tgId": tg_id,
            "expiryTime": expiry_time,
            "totalGB": total_gb,
            "enable": True,
            "flow": "",
            "limitIp": 0,
        }

        for inbound_id in inbound_ids:
            inbound = await self.get_inbound(inbound_id)
            if not inbound:
                logger.warning(f"Cannot get inbound {inbound_id}")
                continue

            clients: list[dict] = inbound.get("settings", {}).get("clients", [])
            # Убираем дубли по email
            clients = [c for c in clients if c.get("email") != email]
            clients.append(new_client)
            inbound["settings"]["clients"] = clients

            ok = await self.update_inbound(inbound_id, inbound)
            if ok:
                logger.info(f"Client {email} added to inbound {inbound_id}")
                return {
                    "email": email,
                    "id": new_client["id"],
                    "uuid": new_client["id"],
                    "subId": str(inbound_id),
                    "inbound_id": inbound_id,
                    "protocol": inbound.get("protocol"),
                    "port": inbound.get("port"),
                }

        return None

    async def delete_client(self, email: str) -> bool:
        """Удалить клиента из всех inbounds."""
        inbounds = await self.get_inbounds()
        for ib in inbounds:
            clients: list[dict] = ib.get("settings", {}).get("clients", [])
            if not any(
                c.get("email") == email or str(c.get("tgId")) == email
                for c in clients
            ):
                continue
            ib["settings"]["clients"] = [
                c for c in clients
                if c.get("email") != email and str(c.get("tgId")) != email
            ]
            await self.update_inbound(ib["id"], ib)
        return True

    async def update_client(
        self,
        email: str,
        expiry_time: int | None = None,
        total_gb: int | None = None,
        enable: bool | None = None,
        tg_id: int | None = None,
    ) -> bool:
        """Обновить параметры клиента во всех inbounds."""
        inbounds = await self.get_inbounds()
        for ib in inbounds:
            clients: list[dict] = ib.get("settings", {}).get("clients", [])
            changed = False
            for c in clients:
                if c.get("email") == email or str(c.get("tgId")) == email:
                    if expiry_time is not None:
                        c["expiryTime"] = expiry_time
                    if total_gb is not None:
                        c["totalGB"] = total_gb
                    if enable is not None:
                        c["enable"] = enable
                    if tg_id is not None:
                        c["tgId"] = tg_id
                    changed = True
            if changed:
                ib["settings"]["clients"] = clients
                await self.update_inbound(ib["id"], ib)
        return True

    async def get_client_traffic(self, email: str) -> dict | None:
        """Трафик клиента — из clientStats первого matching inbound."""
        inbounds = await self.get_inbounds()
        for ib in inbounds:
            stats: list[dict] = ib.get("clientStats", [])
            for s in stats:
                if s.get("email") == email or str(s.get("id")) == email:
                    return s
        return None

    async def get_online_clients(self) -> list[str]:
        """Список email клиентов онлайн."""
        return []

    # ─── Subscription ──────────────────────────────────────────

    def generate_subscription_url(self, sub_id: str) -> str:
        """Subscription URL из настроек."""
        return f"{settings.xui_sub_base_url}{settings.xui_sub_path}{sub_id}"

    # ─── Server ─────────────────────────────────────────────────

    async def check_connection(self) -> bool:
        """Проверка соединения с 3X-UI API."""
        try:
            result = await self._request("GET", "/inbounds/options")
            return result.get("success", False)
        except Exception:
            return False


_xui_service: XUIService | None = None


def get_xui_service() -> XUIService:
    """Получить экземпляр X-UI сервиса."""
    global _xui_service
    if _xui_service is None:
        _xui_service = XUIService()
    return _xui_service
