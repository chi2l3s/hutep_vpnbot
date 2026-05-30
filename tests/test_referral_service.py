"""Tests for bot.services.referral_service module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta


class TestReferralService:
    """Tests for ReferralService class."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock AsyncSession."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def referral_service(self):
        """Create ReferralService instance."""
        from bot.services.referral_service import ReferralService
        return ReferralService()

    @pytest.mark.asyncio
    async def test_generate_referral_link(self, referral_service):
        """Test referral link generation."""
        link = referral_service.generate_referral_link("HutepVPNBot", "HV-ABC123")
        assert "t.me" in link
        assert "HutepVPNBot" in link
        assert "HV-ABC123" in link

    @pytest.mark.asyncio
    async def test_generate_referral_link_empty_username(self, referral_service):
        """Test referral link with empty username."""
        link = referral_service.generate_referral_link("", "HV-ABC123")
        assert "HV-ABC123" in link

    @pytest.mark.asyncio
    async def test_get_user_by_referral_code_found(self, referral_service, mock_session):
        """Test get_user_by_referral_code returns user when found."""
        mock_user = MagicMock()
        mock_user.referral_code = "HV-ABC123"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await referral_service.get_user_by_referral_code(mock_session, "HV-ABC123")
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_get_user_by_referral_code_not_found(self, referral_service, mock_session):
        """Test get_user_by_referral_code returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await referral_service.get_user_by_referral_code(mock_session, "HV-NOTFOUND")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_referral_count(self, referral_service, mock_session):
        """Test get_referral_count returns correct count."""
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[MagicMock(), MagicMock()])
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        count = await referral_service.get_referral_count(mock_session, 123)
        assert count == 2

    @pytest.mark.asyncio
    async def test_get_referral_count_zero(self, referral_service, mock_session):
        """Test get_referral_count returns 0 when no referrals."""
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        count = await referral_service.get_referral_count(mock_session, 123)
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_referral_list(self, referral_service, mock_session):
        """Test get_referral_list returns list of referrals."""
        mock_user1 = MagicMock()
        mock_user1.full_name = "Referral 1"
        mock_user2 = MagicMock()
        mock_user2.full_name = "Referral 2"

        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[mock_user1, mock_user2])
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await referral_service.get_referral_list(mock_session, 123)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_referral_list_empty(self, referral_service, mock_session):
        """Test get_referral_list returns empty list when no referrals."""
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await referral_service.get_referral_list(mock_session, 123)
        assert result == []


class TestApplyReferralBonus:
    """Tests for apply_referral_bonus method."""

    @pytest.mark.asyncio
    async def test_apply_bonus_no_referrer(self):
        """Test that bonus is not applied when bonus_days is 0."""
        with patch("bot.services.referral_service.settings") as mock_settings:
            mock_settings.referral_bonus_days = 0

            from bot.services.referral_service import ReferralService
            mock_session = AsyncMock()
            mock_user = MagicMock()
            mock_user.id = 123
            mock_user.referred_by = None

            result = await ReferralService.apply_referral_bonus(mock_session, mock_user)
            assert result is False

    @pytest.mark.asyncio
    async def test_apply_bonus_success(self):
        """Test successful bonus application."""
        with patch("bot.services.referral_service.settings") as mock_settings:
            mock_settings.referral_bonus_days = 7

            from bot.services.referral_service import ReferralService
            mock_session = AsyncMock()
            mock_referrer = MagicMock()
            mock_referrer.id = 999

            mock_user = MagicMock()
            mock_user.id = 123
            mock_user.referred_by = 999

            # Mock _add_bonus_to_subscription to avoid actual DB calls
            with patch.object(ReferralService, "_add_bonus_to_subscription", new_callable=AsyncMock):
                result = await ReferralService.apply_referral_bonus(mock_session, mock_user)
                assert result is True
                mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_apply_bonus_referrer_not_found(self):
        """Test bonus application when referrer is not found."""
        with patch("bot.services.referral_service.settings") as mock_settings:
            mock_settings.referral_bonus_days = 7

            from bot.services.referral_service import ReferralService
            mock_session = AsyncMock()
            mock_user = MagicMock()
            mock_user.id = 123
            mock_user.referred_by = 999

            # Mock session.get to return None for referrer
            mock_session.get = AsyncMock(side_effect=[
                mock_user,  # First call: get user
                None,       # Second call: get referrer (not found)
            ])

            with patch.object(ReferralService, "_add_bonus_to_subscription", new_callable=AsyncMock):
                result = await ReferralService.apply_referral_bonus(mock_session, mock_user)
                assert result is True


class TestAddBonusToSubscription:
    """Tests for _add_bonus_to_subscription method."""

    @pytest.mark.asyncio
    async def test_add_bonus_to_existing_subscription(self):
        """Test adding bonus to an existing active subscription."""
        from bot.services.referral_service import ReferralService

        mock_session = AsyncMock()
        mock_subscription = MagicMock()
        mock_subscription.end_date = datetime.utcnow() + timedelta(days=10)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_subscription)
        mock_session.execute = AsyncMock(return_value=mock_result)

        await ReferralService._add_bonus_to_subscription(mock_session, 123, 7)

        # Verify subscription was updated
        assert mock_subscription.days == 7
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_bonus_creates_new_subscription(self):
        """Test adding bonus creates new subscription when none exists."""
        from bot.services.referral_service import ReferralService

        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        await ReferralService._add_bonus_to_subscription(mock_session, 123, 7)

        # Verify new subscription was created
        mock_session.add.assert_called_once()
        added_subscription = mock_session.add.call_args[0][0]
        assert added_subscription.user_id == 123
        assert added_subscription.days == 7
        assert added_subscription.is_active is True