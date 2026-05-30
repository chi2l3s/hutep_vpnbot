"""Tests for bot.db.models module."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


class TestUserModel:
    """Tests for User model."""

    def test_generate_referral_code_format(self):
        """Test that referral code has correct format."""
        from bot.db.models import User
        code = User.generate_referral_code()
        assert code.startswith("HV-")
        assert len(code) == 9  # "HV-" + 6 chars

    def test_generate_referral_code_unique(self):
        """Test that generated codes are unique."""
        from bot.db.models import User
        codes = [User.generate_referral_code() for _ in range(100)]
        assert len(codes) == len(set(codes))

    def test_generate_referral_code_chars(self):
        """Test that referral code uses allowed characters."""
        from bot.db.models import User
        import string
        code = User.generate_referral_code()
        prefix, body = code.split("-")
        assert prefix == "HV"
        assert all(c in string.ascii_uppercase + string.digits for c in body)


class TestSubscriptionModel:
    """Tests for Subscription model."""

    def test_is_valid_active_future(self):
        """Test is_valid when subscription is active and not expired."""
        from bot.db.models import Subscription
        sub = Subscription(
            id=1,
            user_id=123,
            days=30,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30),
            is_active=True,
        )
        assert sub.is_valid is True

    def test_is_valid_inactive(self):
        """Test is_valid when subscription is not active."""
        from bot.db.models import Subscription
        sub = Subscription(
            id=1,
            user_id=123,
            days=30,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30),
            is_active=False,
        )
        assert sub.is_valid is False

    def test_is_valid_expired(self):
        """Test is_valid when subscription has expired."""
        from bot.db.models import Subscription
        sub = Subscription(
            id=1,
            user_id=123,
            days=30,
            start_date=datetime.utcnow() - timedelta(days=60),
            end_date=datetime.utcnow() - timedelta(days=30),
            is_active=True,
        )
        assert sub.is_valid is False

    def test_days_remaining_active(self):
        """Test days_remaining for active subscription."""
        from bot.db.models import Subscription
        sub = Subscription(
            id=1,
            user_id=123,
            days=30,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=15),
            is_active=True,
        )
        assert 14 <= sub.days_remaining <= 15

    def test_days_remaining_expired(self):
        """Test days_remaining for expired subscription."""
        from bot.db.models import Subscription
        sub = Subscription(
            id=1,
            user_id=123,
            days=30,
            start_date=datetime.utcnow() - timedelta(days=60),
            end_date=datetime.utcnow() - timedelta(days=30),
            is_active=True,
        )
        assert sub.days_remaining == 0

    def test_days_remaining_inactive(self):
        """Test days_remaining for inactive subscription."""
        from bot.db.models import Subscription
        sub = Subscription(
            id=1,
            user_id=123,
            days=30,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30),
            is_active=False,
        )
        assert sub.days_remaining == 0


class TestPaymentModel:
    """Tests for Payment model."""

    def test_to_stars_amount_with_stars(self):
        """Test to_stars_amount when amount_stars is set."""
        from bot.db.models import Payment
        payment = Payment(
            id=1,
            user_id=123,
            amount=70.0,
            amount_stars=56,
            days=30,
            status="pending",
            payment_method="stars",
        )
        assert payment.to_stars_amount() == 56

    def test_to_stars_amount_without_stars(self):
        """Test to_stars_amount when amount_stars is None."""
        from bot.db.models import Payment
        payment = Payment(
            id=1,
            user_id=123,
            amount=70.0,
            amount_stars=None,
            days=30,
            status="pending",
            payment_method="crypto",
        )
        # 70 / 0.2 = 350
        assert payment.to_stars_amount() == 350

    def test_to_stars_amount_rounds_down(self):
        """Test to_stars_amount rounds down correctly."""
        from bot.db.models import Payment
        payment = Payment(
            id=1,
            user_id=123,
            amount=1.0,
            amount_stars=None,
            days=1,
            status="pending",
            payment_method="crypto",
        )
        # 1 / 0.2 = 5.0
        assert payment.to_stars_amount() == 5


class TestDatabaseFunctions:
    """Tests for database connection functions."""

    def test_get_database_url_uses_settings(self):
        """Test that get_database_url reads from settings."""
        with patch("bot.db.models.settings") as mock_settings:
            mock_settings.database_url = "sqlite+aiosqlite:///test.db"
            from bot.db.models import get_database_url
            # Need to reimport to get the patched version
            import importlib
            import bot.db.models
            importlib.reload(bot.db.models)
            url = bot.db.models.get_database_url()
            assert "test.db" in url
