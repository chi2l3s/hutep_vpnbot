"""Tests for bot.utils.date_utils module."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch


class TestDaysFromNow:
    """Tests for days_from_now function."""

    def test_days_from_now_zero(self):
        """Test days_from_now with 0 days."""
        from bot.utils.date_utils import days_from_now

        result = days_from_now(0)
        now = datetime.utcnow()

        # Should be very close to now
        diff = abs((result - now).total_seconds())
        assert diff < 5  # Within 5 seconds

    def test_days_from_now_positive(self):
        """Test days_from_now with positive number of days."""
        from bot.utils.date_utils import days_from_now

        result = days_from_now(30)
        now = datetime.utcnow()

        expected = now + timedelta(days=30)
        diff = abs((result - expected).total_seconds())
        assert diff < 5  # Within 5 seconds

    def test_days_from_now_negative(self):
        """Test days_from_now with negative number (goes back)."""
        from bot.utils.date_utils import days_from_now

        result = days_from_now(-10)
        now = datetime.utcnow()

        expected = now - timedelta(days=10)
        diff = abs((result - expected).total_seconds())
        assert diff < 5


class TestExtendSubscription:
    """Tests for extend_subscription function."""

    def test_extend_active_subscription(self):
        """Test extending an active (not expired) subscription."""
        from bot.utils.date_utils import extend_subscription

        current_end = datetime.utcnow() + timedelta(days=10)
        result = extend_subscription(current_end, 7)

        expected = current_end + timedelta(days=7)
        assert result == expected

    def test_extend_expired_subscription(self):
        """Test extending an expired subscription (starts from now)."""
        from bot.utils.date_utils import extend_subscription

        current_end = datetime.utcnow() - timedelta(days=5)
        result = extend_subscription(current_end, 7)

        now = datetime.utcnow()
        expected = now + timedelta(days=7)
        diff = abs((result - expected).total_seconds())
        assert diff < 5

    def test_extend_with_large_days(self):
        """Test extending with a large number of days."""
        from bot.utils.date_utils import extend_subscription

        current_end = datetime.utcnow() + timedelta(days=100)
        result = extend_subscription(current_end, 365)

        expected = current_end + timedelta(days=365)
        assert result == expected


class TestFormatDaysRemaining:
    """Tests for format_days_remaining function."""

    def test_format_zero_days(self):
        """Test formatting 0 days."""
        from bot.utils.date_utils import format_days_remaining

        result = format_days_remaining(0)
        assert result == "менее 1 дня"

    def test_format_one_day(self):
        """Test formatting 1 day."""
        from bot.utils.date_utils import format_days_remaining

        result = format_days_remaining(1)
        assert result == "1 день"

    def test_format_two_days(self):
        """Test formatting 2 days (genitive plural)."""
        from bot.utils.date_utils import format_days_remaining

        result = format_days_remaining(2)
        assert result == "2 дня"

    def test_format_three_days(self):
        """Test formatting 3 days (genitive plural)."""
        from bot.utils.date_utils import format_days_remaining

        result = format_days_remaining(3)
        assert result == "3 дня"

    def test_format_four_days(self):
        """Test formatting 4 days (genitive plural)."""
        from bot.utils.date_utils import format_days_remaining

        result = format_days_remaining(4)
        assert result == "4 дня"

    def test_format_five_days(self):
        """Test formatting 5 days (default plural)."""
        from bot.utils.date_utils import format_days_remaining

        result = format_days_remaining(5)
        assert result == "5 дней"

    def test_format_many_days(self):
        """Test formatting many days."""
        from bot.utils.date_utils import format_days_remaining

        result = format_days_remaining(100)
        assert result == "100 дней"

    def test_format_large_number(self):
        """Test formatting a large number of days."""
        from bot.utils.date_utils import format_days_remaining

        result = format_days_remaining(360)
        assert result == "360 дней"


class TestFormatDate:
    """Tests for format_date function."""

    def test_format_date_basic(self):
        """Test basic date formatting."""
        from bot.utils.date_utils import format_date

        dt = datetime(2024, 12, 25, 15, 30, 0)
        result = format_date(dt)
        assert result == "25.12.2024"

    def test_format_date_leading_zero(self):
        """Test date formatting with leading zeros."""
        from bot.utils.date_utils import format_date

        dt = datetime(2024, 1, 5, 0, 0, 0)
        result = format_date(dt)
        assert result == "05.01.2024"


class TestFormatDateTime:
    """Tests for format_datetime function."""

    def test_format_datetime_basic(self):
        """Test basic datetime formatting."""
        from bot.utils.date_utils import format_datetime

        dt = datetime(2024, 12, 25, 14, 30, 0)
        result = format_datetime(dt)
        assert result == "25.12.2024 в 14:30"

    def test_format_datetime_midnight(self):
        """Test datetime formatting at midnight."""
        from bot.utils.date_utils import format_datetime

        dt = datetime(2024, 1, 1, 0, 0, 0)
        result = format_datetime(dt)
        assert result == "01.01.2024 в 00:00"

    def test_format_datetime_evening(self):
        """Test datetime formatting in the evening."""
        from bot.utils.date_utils import format_datetime

        dt = datetime(2024, 6, 15, 21, 45, 0)
        result = format_datetime(dt)
        assert result == "15.06.2024 в 21:45"