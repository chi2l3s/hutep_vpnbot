"""Tests for bot.config module."""

import pytest
from pathlib import Path


class TestSettings:
    """Tests for Settings class."""

    def test_default_values(self):
        """Test that Settings has correct defaults."""
        from bot.config import Settings
        s = Settings()
        assert s.xui_api_url == "http://localhost:20561"
        assert s.xui_use_tls is False
        assert s.database_url == "sqlite+aiosqlite:///./data/hutep_vpn.db"
        assert s.referral_bonus_days == 7
        assert s.webhook_path == "/webhook"
        assert s.webapp_host == "0.0.0.0"
        assert s.webapp_port == 8080
        assert s.proxy == ""

    def test_admin_list_property_empty(self):
        """Test admin_list property returns empty list when admin_ids is empty."""
        from bot.config import Settings
        s = Settings(model_dump=())
        s.__dict__["admin_ids"] = ""
        assert s.admin_list == []

    def test_admin_list_property_single_id(self):
        """Test admin_list with single admin ID."""
        from bot.config import Settings
        s = Settings(model_dump=())
        s.__dict__["admin_ids"] = "111222333"
        assert s.admin_list == [111222333]

    def test_admin_list_property_multiple_ids(self):
        """Test admin_list with multiple admin IDs."""
        from bot.config import Settings
        s = Settings(model_dump=())
        s.__dict__["admin_ids"] = "111222333, 444555666, 777888999"
        assert s.admin_list == [111222333, 444555666, 777888999]

    def test_admin_list_ignores_invalid(self):
        """Test admin_list ignores non-numeric values."""
        from bot.config import Settings
        s = Settings(model_dump=())
        s.__dict__["admin_ids"] = "111222333, invalid, 777888999"
        assert s.admin_list == [111222333, 777888999]

    def test_admin_list_strips_whitespace(self):
        """Test admin_list strips whitespace from IDs."""
        from bot.config import Settings
        s = Settings(model_dump=())
        s.__dict__["admin_ids"] = "  111222333  ,  444555666  "
        assert s.admin_list == [111222333, 444555666]

    def test_subscription_plans_all_keys_present(self):
        """Test subscription_plans has all expected keys."""
        from bot.config import Settings
        s = Settings()
        plans = s.subscription_plans
        assert set(plans.keys()) == {30, 90, 180, 360}

    def test_subscription_plans_prices_increase_with_duration(self):
        """Test that longer plans are more expensive."""
        from bot.config import Settings
        s = Settings()
        plans = s.subscription_plans
        assert plans[30]["price"] == 70
        assert plans[90]["price"] == 190
        assert plans[180]["price"] == 350
        assert plans[360]["price"] == 600

    def test_subscription_plans_days_match_keys(self):
        """Test that plan days match the dictionary keys."""
        from bot.config import Settings
        s = Settings()
        plans = s.subscription_plans
        for days, plan in plans.items():
            assert plan["days"] == days

    def test_subscription_plans_all_have_names(self):
        """Test that all plans have name field."""
        from bot.config import Settings
        s = Settings()
        plans = s.subscription_plans
        for days, plan in plans.items():
            assert "name" in plan
            assert isinstance(plan["name"], str)

    def test_db_path_returns_path_object(self):
        """Test db_path property returns Path."""
        from bot.config import Settings
        s = Settings()
        assert isinstance(s.db_path, Path)
        assert "hutep_vpn.db" in str(s.db_path)

    def test_price_per_day_decreases_with_longer_plans(self):
        """Test that price per day is lower for longer plans."""
        from bot.config import Settings
        s = Settings()
        plans = s.subscription_plans
        ppd = {days: plans[days]["price"] / plans[days]["days"] for days in plans}
        assert ppd[360] < ppd[180] < ppd[90] < ppd[30]

    def test_xui_sub_urls_configured(self):
        """Test X-UI subscription URLs are configured."""
        from bot.config import Settings
        s = Settings()
        assert s.xui_sub_base_url == "https://vpn.mylumina.ru:2096"
        assert s.xui_sub_path == "/sub/"
