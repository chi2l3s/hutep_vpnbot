"""Tests for bot.keyboards.inline module."""

import pytest
from unittest.mock import patch, MagicMock
from bot.keyboards.inline import (
    get_main_menu_inline_keyboard,
    get_subscription_plans_keyboard,
    get_payment_methods_keyboard,
    get_back_to_subscription_keyboard,
    get_profile_keyboard,
    get_referral_keyboard,
    get_vpn_profiles_keyboard,
    get_help_keyboard,
    get_confirm_payment_keyboard,
    get_admin_keyboard,
    get_admin_users_keyboard,
    get_admin_user_actions_keyboard,
    get_admin_days_keyboard,
)


class TestMainMenuKeyboard:
    """Tests for main menu keyboard."""

    def test_main_menu_structure(self):
        """Test main menu has correct button structure."""
        from bot.config import Settings
        s = Settings()
        with patch("bot.keyboards.inline.settings", s):
            kb = get_main_menu_inline_keyboard()

            assert kb is not None
            assert hasattr(kb, "inline_keyboard")
            assert len(kb.inline_keyboard) >= 3

    def test_main_menu_admin_button_added(self):
        """Test admin button is added when is_admin=True."""
        with patch("bot.keyboards.inline.settings") as mock_settings:
            mock_settings.subscription_plans = {
                30: {"price": 70, "days": 30, "name": "Basic"},
            }
            kb = get_main_menu_inline_keyboard(is_admin=True)

            # Should have one more row than non-admin
            kb_normal = get_main_menu_inline_keyboard(is_admin=False)

            assert len(kb.inline_keyboard) == len(kb_normal.inline_keyboard) + 1

    def test_main_menu_all_buttons_present(self):
        """Test all expected buttons are present."""
        with patch("bot.keyboards.inline.settings") as mock_settings:
            mock_settings.subscription_plans = {
                30: {"price": 70, "days": 30, "name": "Basic"},
            }
            kb = get_main_menu_inline_keyboard()

            all_button_texts = []
            for row in kb.inline_keyboard:
                for button in row:
                    all_button_texts.append(button.text)

            # Check for main menu buttons
            assert any("Мой кабинет" in text for text in all_button_texts)
            assert any("VPN профили" in text for text in all_button_texts)
            assert any("Оформить подписку" in text for text in all_button_texts)
            assert any("Рефералы" in text for text in all_button_texts)


class TestSubscriptionPlansKeyboard:
    """Tests for subscription plans keyboard."""

    def test_all_plans_shown(self):
        """Test all subscription plans are shown."""
        with patch("bot.keyboards.inline.settings") as mock_settings:
            mock_settings.subscription_plans = {
                30: {"price": 70, "days": 30, "name": "Basic"},
                90: {"price": 190, "days": 90, "name": "Popular"},
                180: {"price": 350, "days": 180, "name": "Premium"},
                360: {"price": 600, "days": 360, "name": "Yearly"},
            }
            kb = get_subscription_plans_keyboard()

            button_callbacks = []
            for row in kb.inline_keyboard:
                for button in row:
                    button_callbacks.append(button.callback_data)

            assert "sub_select_30" in button_callbacks
            assert "sub_select_90" in button_callbacks
            assert "sub_select_180" in button_callbacks
            assert "sub_select_360" in button_callbacks

    def test_back_button_present(self):
        """Test back button is present."""
        with patch("bot.keyboards.inline.settings") as mock_settings:
            mock_settings.subscription_plans = {
                30: {"price": 70, "days": 30, "name": "Basic"},
            }
            kb = get_subscription_plans_keyboard()

            back_button_found = False
            for row in kb.inline_keyboard:
                for button in row:
                    if "menu_main" in (button.callback_data or ""):
                        back_button_found = True

            assert back_button_found


class TestPaymentMethodsKeyboard:
    """Tests for payment methods keyboard."""

    def test_stars_button_present(self):
        """Test Telegram Stars button is present."""
        with patch("bot.keyboards.inline.settings") as mock_settings:
            mock_settings.subscription_plans = {
                30: {"price": 70, "days": 30, "name": "Basic"},
            }
            kb = get_payment_methods_keyboard(30)

            stars_button_found = False
            for row in kb.inline_keyboard:
                for button in row:
                    if "pay_stars_30" in (button.callback_data or ""):
                        stars_button_found = True

            assert stars_button_found

    def test_crypto_button_present(self):
        """Test cryptocurrency button is present."""
        with patch("bot.keyboards.inline.settings") as mock_settings:
            mock_settings.subscription_plans = {
                30: {"price": 70, "days": 30, "name": "Basic"},
            }
            kb = get_payment_methods_keyboard(30)

            crypto_button_found = False
            for row in kb.inline_keyboard:
                for button in row:
                    if "pay_crypto_30" in (button.callback_data or ""):
                        crypto_button_found = True

            assert crypto_button_found

    def test_back_button_present(self):
        """Test back button is present."""
        with patch("bot.keyboards.inline.settings") as mock_settings:
            mock_settings.subscription_plans = {
                30: {"price": 70, "days": 30, "name": "Basic"},
            }
            kb = get_payment_methods_keyboard(30)

            back_button_found = False
            for row in kb.inline_keyboard:
                for button in row:
                    if "sub_select_30" in (button.callback_data or ""):
                        back_button_found = True

            assert back_button_found


class TestProfileKeyboard:
    """Tests for profile keyboard."""

    def test_has_subscription_buy_button(self):
        """Test keyboard shows 'Buy subscription' when no subscription."""
        with patch("bot.keyboards.inline.settings"):
            kb = get_profile_keyboard(has_subscription=False)

            button_texts = [btn.text for row in kb.inline_keyboard for btn in row]
            assert any("Купить подписку" in text for text in button_texts)

    def test_has_subscription_renew_button(self):
        """Test keyboard shows 'Renew subscription' when has subscription."""
        with patch("bot.keyboards.inline.settings"):
            kb = get_profile_keyboard(has_subscription=True)

            button_texts = [btn.text for row in kb.inline_keyboard for btn in row]
            assert any("Продлить подписку" in text for text in button_texts)


class TestVPNProfilesKeyboard:
    """Tests for VPN profiles keyboard."""

    def test_vpn_show_button_present(self):
        """Test 'Show profile' button is present."""
        kb = get_vpn_profiles_keyboard()

        show_button_found = False
        for row in kb.inline_keyboard:
            for button in row:
                if button.callback_data == "vpn_show":
                    show_button_found = True

        assert show_button_found

    def test_vpn_regenerate_button_present(self):
        """Test 'Regenerate profile' button is present."""
        kb = get_vpn_profiles_keyboard()

        regenerate_button_found = False
        for row in kb.inline_keyboard:
            for button in row:
                if button.callback_data == "vpn_regenerate":
                    regenerate_button_found = True

        assert regenerate_button_found

    def test_vpn_instructions_button_present(self):
        """Test 'Instructions' button is present."""
        kb = get_vpn_profiles_keyboard()

        instructions_button_found = False
        for row in kb.inline_keyboard:
            for button in row:
                if button.callback_data == "vpn_instructions":
                    instructions_button_found = True

        assert instructions_button_found


class TestAdminKeyboards:
    """Tests for admin keyboards."""

    def test_admin_users_button(self):
        """Test admin users button is present."""
        kb = get_admin_keyboard()

        users_button_found = False
        for row in kb.inline_keyboard:
            for button in row:
                if button.callback_data == "admin_users":
                    users_button_found = True

        assert users_button_found

    def test_admin_stats_button(self):
        """Test admin stats button is present."""
        kb = get_admin_keyboard()

        stats_button_found = False
        for row in kb.inline_keyboard:
            for button in row:
                if button.callback_data == "admin_stats":
                    stats_button_found = True

        assert stats_button_found

    def test_admin_users_keyboard_with_users(self):
        """Test admin users keyboard with mock users."""
        mock_user1 = MagicMock()
        mock_user1.id = 123
        mock_user1.full_name = "Test User 1"

        mock_user2 = MagicMock()
        mock_user2.id = 456
        mock_user2.full_name = "Test User 2"

        kb = get_admin_users_keyboard([mock_user1, mock_user2])

        user_buttons_found = 0
        for row in kb.inline_keyboard:
            for button in row:
                if button.callback_data.startswith("admin_user_"):
                    user_buttons_found += 1

        assert user_buttons_found == 2

    def test_admin_user_actions_keyboard(self):
        """Test admin user actions keyboard has day options."""
        with patch("bot.keyboards.inline.settings") as mock_settings:
            mock_settings.subscription_plans = {
                30: {"price": 70},
                90: {"price": 190},
                180: {"price": 350},
                360: {"price": 600},
            }
            kb = get_admin_user_actions_keyboard(123)

            day_buttons = []
            for row in kb.inline_keyboard:
                for button in row:
                    if button.callback_data.startswith("admin_confirm_123_"):
                        day_buttons.append(button.callback_data)

            assert any("admin_confirm_123_30" in b for b in day_buttons)
            assert any("admin_confirm_123_90" in b for b in day_buttons)
            assert any("admin_confirm_123_180" in b for b in day_buttons)
            assert any("admin_confirm_123_360" in b for b in day_buttons)


class TestHelpKeyboard:
    """Tests for help keyboard."""

    def test_servers_status_button(self):
        """Test servers status button is present."""
        kb = get_help_keyboard()

        status_button_found = False
        for row in kb.inline_keyboard:
            for button in row:
                if button.callback_data == "help_servers":
                    status_button_found = True

        assert status_button_found

    def test_support_button(self):
        """Test support button is present."""
        kb = get_help_keyboard()

        support_button_found = False
        for row in kb.inline_keyboard:
            for button in row:
                if button.callback_data == "help_support":
                    support_button_found = True

        assert support_button_found


class TestReferralKeyboard:
    """Tests for referral keyboard."""

    def test_how_it_works_button(self):
        """Test 'How it works' button is present."""
        kb = get_referral_keyboard()

        how_button_found = False
        for row in kb.inline_keyboard:
            for button in row:
                if button.callback_data == "referral_help":
                    how_button_found = True

        assert how_button_found

    def test_back_button_present(self):
        """Test back button is present."""
        kb = get_referral_keyboard()

        back_button_found = False
        for row in kb.inline_keyboard:
            for button in row:
                if "menu_main" in (button.callback_data or ""):
                    back_button_found = True

        assert back_button_found


class TestConfirmPaymentKeyboard:
    """Tests for confirm payment keyboard."""

    def test_check_payment_button(self):
        """Test check payment button is present."""
        kb = get_confirm_payment_keyboard("inv_123")

        check_button_found = False
        for row in kb.inline_keyboard:
            for button in row:
                if button.callback_data == "check_payment_inv_123":
                    check_button_found = True

        assert check_button_found

    def test_cancel_button(self):
        """Test cancel button is present."""
        kb = get_confirm_payment_keyboard("inv_123")

        cancel_button_found = False
        for row in kb.inline_keyboard:
            for button in row:
                if button.callback_data == "subscribe":
                    cancel_button_found = True

        assert cancel_button_found