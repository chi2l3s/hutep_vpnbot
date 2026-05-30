"""Tests for bot.services.vpn_service module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta


class TestVPNService:
    """Tests for VPNService class."""

    @pytest.fixture
    def vpn_service(self):
        """Create VPNService instance with mocked X-UI service."""
        with patch("bot.services.vpn_service.get_xui_service") as mock_get_xui:
            mock_xui = MagicMock()
            mock_xui.generate_subscription_url = MagicMock(
                return_value="https://vpn.example.com/sub/sub123"
            )
            mock_get_xui.return_value = mock_xui

            from bot.services.vpn_service import VPNService, VPNServiceError
            return VPNService()

    @pytest.mark.asyncio
    async def test_get_or_create_profile_existing(self, vpn_service, mock_session, mock_user):
        """Test get_or_create_profile returns existing profile."""
        mock_profile = MagicMock()
        mock_profile.profile_link = "https://vpn.example.com/sub/existing"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_profile)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await vpn_service.get_or_create_profile(mock_session, mock_user)

        assert result == mock_profile
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_profile_creates_new(self, vpn_service, mock_session, mock_user):
        """Test get_or_create_profile creates new profile."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_xui_client = MagicMock()
        mock_xui_client.get = MagicMock(side_effect=lambda k, d=None: {
            "id": "uuid-123", "subId": "sub123"
        }.get(k, d))
        vpn_service.xui.create_client = AsyncMock(return_value={
            "id": "uuid-123",
            "subId": "sub123",
        })

        result = await vpn_service.get_or_create_profile(mock_session, mock_user)

        vpn_service.xui.create_client.assert_called_once()
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_profile_xui_failure(self, vpn_service, mock_session, mock_user):
        """Test get_or_create_profile raises error on X-UI failure."""
        from bot.services.vpn_service import VPNServiceError

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        vpn_service.xui.create_client = AsyncMock(return_value=None)

        with pytest.raises(VPNServiceError):
            await vpn_service.get_or_create_profile(mock_session, mock_user)

    @pytest.mark.asyncio
    async def test_get_profile_found(self, vpn_service, mock_session):
        """Test get_profile returns profile when found."""
        mock_profile = MagicMock()
        mock_profile.profile_link = "https://vpn.example.com/sub/test"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_profile)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await vpn_service.get_profile(mock_session, 123456789)

        assert result == mock_profile

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, vpn_service, mock_session):
        """Test get_profile returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await vpn_service.get_profile(mock_session, 999)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_profile_not_found(self, vpn_service, mock_session):
        """Test delete_profile returns False when profile not found."""
        vpn_service.get_profile = AsyncMock(return_value=None)

        result = await vpn_service.delete_profile(mock_session, 999)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_profile_success(self, vpn_service, mock_session):
        """Test delete_profile successfully deactivates profile."""
        mock_profile = MagicMock()
        mock_profile.is_active = True
        vpn_service.get_profile = AsyncMock(return_value=mock_profile)
        vpn_service.xui.delete_client = AsyncMock(return_value=True)

        result = await vpn_service.delete_profile(mock_session, 123456789)

        assert result is True
        assert mock_profile.is_active is False
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_profile_xui_failure(self, vpn_service, mock_session):
        """Test delete_profile returns False when X-UI delete fails."""
        from bot.services.vpn_service import XUIServiceError

        mock_profile = MagicMock()
        mock_profile.is_active = True
        vpn_service.get_profile = AsyncMock(return_value=mock_profile)
        vpn_service.xui.delete_client = AsyncMock(side_effect=XUIServiceError("API error"))

        result = await vpn_service.delete_profile(mock_session, 123456789)

        assert result is False


class TestVPNServiceError:
    """Tests for VPNServiceError exception."""

    def test_vpn_service_error_message(self):
        """Test VPNServiceError can be raised with message."""
        from bot.services.vpn_service import VPNServiceError

        with pytest.raises(VPNServiceError) as exc_info:
            raise VPNServiceError("Test error message")

        assert str(exc_info.value) == "Test error message"


class TestCheckUserSubscription:
    """Tests for check_user_subscription method."""

    @pytest.fixture
    def vpn_service(self):
        """Create VPNService instance with mocked X-UI service."""
        with patch("bot.services.vpn_service.get_xui_service") as mock_get_xui:
            mock_xui = MagicMock()
            mock_get_xui.return_value = mock_xui
            from bot.services.vpn_service import VPNService
            return VPNService()

    @pytest.mark.asyncio
    async def test_check_subscription_valid(self, vpn_service, mock_session):
        """Test check_user_subscription returns valid subscription."""
        mock_subscription = MagicMock()
        mock_subscription.is_valid = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_subscription)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await vpn_service.check_user_subscription(mock_session, 123)

        assert result == mock_subscription
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_subscription_expired_deactivates(self, vpn_service, mock_session):
        """Test check_user_subscription deactivates expired subscription."""
        mock_subscription = MagicMock()
        mock_subscription.is_valid = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_subscription)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await vpn_service.check_user_subscription(mock_session, 123)

        assert result is None
        assert mock_subscription.is_active is False
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_subscription_not_found(self, vpn_service, mock_session):
        """Test check_user_subscription returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await vpn_service.check_user_subscription(mock_session, 999)

        assert result is None