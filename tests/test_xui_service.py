"""Tests for bot.services.xui_service module."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import aiohttp


class TestXUIService:
    """Tests for XUIService class."""

    @pytest.fixture
    def xui_service(self):
        """Create XUIService instance with mocked settings."""
        with patch("bot.services.xui_service.settings") as mock_settings:
            mock_settings.xui_api_url = "http://localhost:20561"
            mock_settings.xui_api_key = "test_api_key"
            mock_settings.xui_sub_base_url = "https://vpn.example.com"
            mock_settings.xui_sub_path = "/sub/"

            from bot.services.xui_service import XUIService
            service = XUIService()
            return service

    def test_init_sets_base_url(self, xui_service):
        """Test that __init__ sets base_url without trailing slash."""
        assert xui_service.base_url == "http://localhost:20561"

    def test_init_sets_api_key(self, xui_service):
        """Test that __init__ sets api_key."""
        assert xui_service.api_key == "test_api_key"

    def test_get_headers_contains_auth(self, xui_service):
        """Test that _get_headers returns correct headers."""
        headers = xui_service._get_headers()
        assert "Content-Type" in headers
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_api_key"

    def test_generate_subscription_url(self, xui_service):
        """Test subscription URL generation."""
        url = xui_service.generate_subscription_url("sub123")
        assert "sub123" in url
        assert url.endswith("/sub123")

    def test_generate_subscription_url_empty(self, xui_service):
        """Test subscription URL with empty sub_id."""
        url = xui_service.generate_subscription_url("")
        assert url.endswith("/sub/")

    @pytest.mark.asyncio
    async def test_check_connection_success(self, xui_service):
        """Test check_connection returns True on success."""
        xui_service.get_inbounds = AsyncMock(return_value=[])
        result = await xui_service.check_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_connection_failure(self, xui_service):
        """Test check_connection returns False on failure."""
        xui_service.get_inbounds = AsyncMock(side_effect=Exception("Connection failed"))
        result = await xui_service.check_connection()
        assert result is False


class TestXUIServiceRequests:
    """Tests for XUIService request methods via aiohttp mocking."""

    @pytest.fixture
    def xui_service(self):
        with patch("bot.services.xui_service.settings") as mock_settings:
            mock_settings.xui_api_url = "http://localhost:20561"
            mock_settings.xui_api_key = "test_api_key"
            mock_settings.xui_sub_base_url = "https://vpn.example.com"
            mock_settings.xui_sub_path = "/sub/"
            from bot.services.xui_service import XUIService
            return XUIService()

    def _build_mock_response(self, status: int, json_data: dict) -> MagicMock:
        """Build a mock aiohttp response that works as async ctx manager."""
        response = MagicMock()
        response.status = status
        # Return sync lambda for json() - called directly in _request
        response.json = lambda: json_data
        response.text = lambda: str(json_data)
        # Make it work as async context manager
        response.__aenter__ = AsyncMock(return_value=response)
        response.__aexit__ = AsyncMock(return_value=None)
        return response

    def _build_mock_session(self, mock_response: MagicMock) -> MagicMock:
        """Build a mock aiohttp session whose request() returns mock_response."""
        mock_session = MagicMock()
        # session.request() is a normal method returning an awaitable.
        # await session.request(...) → await AsyncMock() → mock_response
        mock_session.request = MagicMock(return_value=AsyncMock(return_value=mock_response))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        return mock_session

    @pytest.mark.asyncio
    async def test_get_inbounds_success(self, xui_service):
        """Test get_inbounds returns list of inbounds."""
        mock_response = self._build_mock_response(200, {"obj": [{"id": 1}, {"id": 2}]})
        mock_session = self._build_mock_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await xui_service.get_inbounds()
            assert result == [{"id": 1}, {"id": 2}]

    @pytest.mark.asyncio
    async def test_get_inbounds_api_error(self, xui_service):
        """Test get_inbounds returns empty list on API error."""
        mock_response = self._build_mock_response(500, {"msg": "Internal error"})
        mock_session = self._build_mock_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await xui_service.get_inbounds()
            assert result == []

    @pytest.mark.asyncio
    async def test_get_client_found(self, xui_service):
        """Test get_client returns client data when found."""
        mock_response = self._build_mock_response(200, {
            "obj": {"email": "123456", "subId": "sub123"}
        })
        mock_session = self._build_mock_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await xui_service.get_client("123456")
            assert result == {"email": "123456", "subId": "sub123"}

    @pytest.mark.asyncio
    async def test_get_client_not_found(self, xui_service):
        """Test get_client returns None when not found."""
        mock_response = self._build_mock_response(404, {"msg": "Not found"})
        mock_session = self._build_mock_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await xui_service.get_client("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_client_connection_error(self, xui_service):
        """Test get_client returns None on connection error."""
        mock_session = self._build_mock_session(MagicMock())
        mock_session.request = AsyncMock(side_effect=aiohttp.ClientError("Connection failed"))

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await xui_service.get_client("test")
            assert result is None

    @pytest.mark.asyncio
    async def test_create_client_success(self, xui_service):
        """Test create_client returns client data on success."""
        mock_response = self._build_mock_response(200, {
            "success": True,
            "obj": {"id": "client-uuid", "email": "123456", "subId": "sub123"}
        })
        mock_session = self._build_mock_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await xui_service.create_client(email="123456", inbound_ids=[1])
            assert result == {"id": "client-uuid", "email": "123456", "subId": "sub123"}

    @pytest.mark.asyncio
    async def test_create_client_failure(self, xui_service):
        """Test create_client returns None on API failure."""
        mock_response = self._build_mock_response(200, {"success": False, "msg": "Failed"})
        mock_session = self._build_mock_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await xui_service.create_client(email="123456", inbound_ids=[1])
            assert result is None

    @pytest.mark.asyncio
    async def test_delete_client_success(self, xui_service):
        """Test delete_client returns True on success."""
        mock_response = self._build_mock_response(200, {"success": True})
        mock_session = self._build_mock_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await xui_service.delete_client("123456")
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_client_failure(self, xui_service):
        """Test delete_client returns False on connection error."""
        mock_session = self._build_mock_session(MagicMock())
        mock_session.request = AsyncMock(side_effect=aiohttp.ClientError("Error"))

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await xui_service.delete_client("123456")
            assert result is False


class TestXUIServiceSingleton:
    """Tests for XUIService singleton."""

    def test_get_xui_service_returns_instance(self):
        """Test get_xui_service returns XUIService instance."""
        with patch("bot.services.xui_service.settings") as mock_settings:
            mock_settings.xui_api_url = "http://localhost:20561"
            mock_settings.xui_api_key = "test_key"
            mock_settings.xui_sub_base_url = "https://vpn.example.com"
            mock_settings.xui_sub_path = "/sub/"

            # Reset singleton
            import bot.services.xui_service
            bot.services.xui_service._xui_service = None

            from bot.services.xui_service import get_xui_service, XUIService
            service = get_xui_service()
            assert isinstance(service, XUIService)

    def test_get_xui_service_same_instance(self):
        """Test get_xui_service returns same instance."""
        with patch("bot.services.xui_service.settings") as mock_settings:
            mock_settings.xui_api_url = "http://localhost:20561"
            mock_settings.xui_api_key = "test_key"
            mock_settings.xui_sub_base_url = "https://vpn.example.com"
            mock_settings.xui_sub_path = "/sub/"

            # Reset singleton
            import bot.services.xui_service
            bot.services.xui_service._xui_service = None

            from bot.services.xui_service import get_xui_service
            service1 = get_xui_service()
            service2 = get_xui_service()
            assert service1 is service2