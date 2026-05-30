"""Tests for bot.utils.text_formatter module."""

import pytest
from unittest.mock import MagicMock, patch


class TestFormatPrice:
    """Tests for format_price function."""

    def test_format_price_basic(self):
        """Test basic price formatting."""
        from bot.utils.text_formatter import format_price

        result = format_price(70.0)
        assert result == "70₽"

    def test_format_price_with_cents(self):
        """Test price formatting with fractional amount."""
        from bot.utils.text_formatter import format_price

        result = format_price(70.99)
        assert result == "71₽"  # Rounds to nearest

    def test_format_price_zero(self):
        """Test price formatting with zero."""
        from bot.utils.text_formatter import format_price

        result = format_price(0)
        assert result == "0₽"

    def test_format_price_large(self):
        """Test price formatting with large amount."""
        from bot.utils.text_formatter import format_price

        result = format_price(999.99)
        assert result == "1000₽"


class TestFormatSubscriptionText:
    """Tests for format_subscription_text function."""

    def test_format_subscription_text_valid(self):
        """Test formatting valid subscription text."""
        from bot.utils.text_formatter import format_subscription_text

        mock_sub = MagicMock()
        mock_sub.is_valid = True
        mock_sub.days_remaining = 25
        mock_sub.end_date = MagicMock()
        mock_sub.end_date.strftime = MagicMock(return_value="25.12.2024")

        # Mock the date_utils functions
        with patch("bot.utils.text_formatter.format_date", return_value="25.12.2024"):
            with patch("bot.utils.text_formatter.format_days_remaining", return_value="25 дней"):
                result = format_subscription_text(mock_sub)

        assert "✅ <b>Подписка активна</b>" in result
        assert "25 дней" in result
        assert "25.12.2024" in result

    def test_format_subscription_text_invalid(self):
        """Test formatting invalid/no subscription text."""
        from bot.utils.text_formatter import format_subscription_text

        result = format_subscription_text(None)

        assert "🚫 <b>Нет активной подписки</b>" in result
        assert "Оформите подписку" in result

    def test_format_subscription_text_expired(self):
        """Test formatting expired subscription."""
        from bot.utils.text_formatter import format_subscription_text

        mock_sub = MagicMock()
        mock_sub.is_valid = False

        result = format_subscription_text(mock_sub)

        assert "🚫 <b>Нет активной подписки</b>" in result


class TestFormatReferralInfo:
    """Tests for format_referral_info function."""

    def test_format_referral_info_basic(self):
        """Test basic referral info formatting."""
        from bot.utils.text_formatter import format_referral_info

        mock_user = MagicMock()
        mock_user.referral_code = "HV-ABC123"

        with patch("bot.utils.text_formatter.settings") as mock_settings:
            mock_settings.bot_token = "123456789:ABCdefGHI"

            result = format_referral_info(mock_user, 5)

        assert "👥 <b>Реферальная программа</b>" in result
        assert "HV-ABC123" in result
        assert "5" in result
        assert "+7 дней" in result

    def test_format_referral_info_zero_referrals(self):
        """Test referral info with zero referrals."""
        from bot.utils.text_formatter import format_referral_info

        mock_user = MagicMock()
        mock_user.referral_code = "HV-XYZ789"

        with patch("bot.utils.text_formatter.settings") as mock_settings:
            mock_settings.bot_token = "123456789:ABCdefGHI"

            result = format_referral_info(mock_user, 0)

        assert "HV-XYZ789" in result


class TestFormatProfileInfo:
    """Tests for format_profile_info function."""

    def test_format_profile_info_active(self):
        """Test formatting active VPN profile."""
        from bot.utils.text_formatter import format_profile_info

        mock_profile = MagicMock()
        mock_profile.protocol = "vless"
        mock_profile.server_name = "HutepVPN Server"
        mock_profile.is_active = True

        result = format_profile_info(mock_profile)

        assert "🔐 <b>VPN Профиль</b>" in result
        assert "VLESS" in result
        assert "HutepVPN Server" in result
        assert "Активен" in result

    def test_format_profile_info_inactive(self):
        """Test formatting inactive VPN profile."""
        from bot.utils.text_formatter import format_profile_info

        mock_profile = MagicMock()
        mock_profile.protocol = "vless"
        mock_profile.server_name = "Test Server"
        mock_profile.is_active = False

        result = format_profile_info(mock_profile)

        assert "Неактивен" in result

    def test_format_profile_info_no_server(self):
        """Test formatting profile with no server name."""
        from bot.utils.text_formatter import format_profile_info

        mock_profile = MagicMock()
        mock_profile.protocol = "vless"
        mock_profile.server_name = None
        mock_profile.is_active = True

        result = format_profile_info(mock_profile)

        assert "Неизвестен" in result