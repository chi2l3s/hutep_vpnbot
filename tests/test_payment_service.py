"""Tests for bot.services.payment_service module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bot.services.payment_service import (
    PaymentService,
    NOWPaymentsProvider,
    InvoiceResult,
    PaymentCheckResult,
    PaymentStatus,
    PaymentMethod,
)


class TestPaymentService:
    """Tests for PaymentService class."""

    @pytest.fixture
    def payment_service(self):
        """Create PaymentService instance."""
        return PaymentService()

    def test_calculate_stars_amount_basic(self, payment_service):
        """Test basic star calculation."""
        # 70 / 0.2 = 350
        result = payment_service.calculate_stars_amount(70.0)
        assert result == 350

    def test_calculate_stars_amount_small_amount(self, payment_service):
        """Test star calculation with small amount."""
        # 0.1 / 0.2 = 0.5, rounded to 0, but min is 1
        result = payment_service.calculate_stars_amount(0.1)
        assert result == 1

    def test_calculate_stars_amount_exact(self, payment_service):
        """Test star calculation with exact amount."""
        # 100 / 0.2 = 500
        result = payment_service.calculate_stars_amount(100.0)
        assert result == 500

    @pytest.mark.asyncio
    async def test_create_stars_invoice_returns_correct_data(self, payment_service):
        """Test create_stars_invoice returns correct structure."""
        result = await payment_service.create_stars_invoice(
            amount_rub=70.0,
            days=30,
            title="HutepVPN 30 дней"
        )

        assert result["title"] == "HutepVPN 30 дней"
        assert result["description"] == "Подписка HutepVPN на 30 дней"
        assert result["payload"] == "sub_30_350"  # 70/0.2 = 350
        assert result["currency"] == "XTR"
        assert result["prices"][0]["label"] == "30 дней подписки"
        assert result["prices"][0]["amount"] == 350


class TestNOWPaymentsProvider:
    """Tests for NOWPaymentsProvider class."""

    @pytest.fixture
    def provider(self):
        """Create NOWPaymentsProvider instance."""
        with patch("bot.services.payment_service.settings") as mock_settings:
            mock_settings.nowpayments_api_key = "test_api_key"
            mock_settings.nowpayments_webhook_secret = "test_secret"
            mock_settings.nowpayments_sandbox = False
            mock_settings.webhook_host = ""
            return NOWPaymentsProvider()

    def test_get_headers(self, provider):
        """Test _get_headers returns correct headers."""
        headers = provider._get_headers()
        assert headers["Content-Type"] == "application/json"
        assert headers["x-api-key"] == "test_api_key"

    @pytest.mark.asyncio
    async def test_handle_webhook_valid(self, provider):
        """Test handle_webhook returns True for valid payment."""
        payload = {
            "id": "123",
            "order_id": "hv_123456789_abc123",
            "payment_status": "finished",
        }
        result = await provider.handle_webhook(payload)
        assert result is True

    @pytest.mark.asyncio
    async def test_handle_webhook_confirmed(self, provider):
        """Test handle_webhook returns True for confirmed payment."""
        payload = {
            "id": "123",
            "order_id": "hv_123456789_abc123",
            "payment_status": "confirmed",
        }
        result = await provider.handle_webhook(payload)
        assert result is True

    @pytest.mark.asyncio
    async def test_handle_webhook_pending(self, provider):
        """Test handle_webhook returns False for pending payment."""
        payload = {
            "id": "123",
            "order_id": "hv_123456789_abc123",
            "payment_status": "pending",
        }
        result = await provider.handle_webhook(payload)
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_webhook_wrong_order_format(self, provider):
        """Test handle_webhook returns False for wrong order format."""
        payload = {
            "id": "123",
            "order_id": "wrong_format",
            "payment_status": "finished",
        }
        result = await provider.handle_webhook(payload)
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_webhook_exception(self, provider):
        """Test handle_webhook handles exceptions gracefully."""
        payload = {}  # Empty payload to cause exception
        result = await provider.handle_webhook(payload)
        assert result is False

    @pytest.mark.asyncio
    async def test_check_payment_returns_pending(self, provider):
        """Test check_payment returns pending status."""
        result = await provider.check_payment("test_invoice_id")
        assert result.is_paid is False
        assert result.status == PaymentStatus.PENDING


class TestPaymentServiceIntegration:
    """Integration tests for PaymentService."""

    @pytest.fixture
    def payment_service(self):
        """Create PaymentService instance."""
        return PaymentService()

    @pytest.mark.asyncio
    async def test_create_crypto_invoice(self, payment_service):
        """Test create_crypto_invoice calls provider correctly."""
        with patch.object(payment_service.crypto_provider, "create_invoice", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = InvoiceResult(
                success=True,
                invoice_id="inv_123",
                payment_url="https://pay.example.com/123"
            )

            result = await payment_service.create_crypto_invoice(
                amount=70.0,
                days=30,
                user_telegram_id=123456789
            )

            assert result.success is True
            assert result.invoice_id == "inv_123"
            mock_create.assert_called_once_with(
                amount=70.0,
                days=30,
                user_telegram_id=123456789
            )

    @pytest.mark.asyncio
    async def test_check_crypto_payment(self, payment_service):
        """Test check_crypto_payment calls provider correctly."""
        with patch.object(payment_service.crypto_provider, "get_payment_status", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = PaymentCheckResult(
                is_paid=True,
                status=PaymentStatus.COMPLETED
            )

            result = await payment_service.check_crypto_payment("inv_123")

            assert result.is_paid is True
            assert result.status == PaymentStatus.COMPLETED
            mock_check.assert_called_once_with("inv_123")

    @pytest.mark.asyncio
    async def test_handle_nowpayments_webhook(self, payment_service):
        """Test handle_nowpayments_webhook calls provider correctly."""
        with patch.object(payment_service.crypto_provider, "handle_webhook", new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = True

            payload = {"order_id": "hv_123_abc", "payment_status": "finished"}
            result = await payment_service.handle_nowpayments_webhook(payload)

            assert result is True
            mock_handle.assert_called_once_with(payload)


class TestInvoiceResult:
    """Tests for InvoiceResult dataclass."""

    def test_invoice_result_success(self):
        """Test InvoiceResult with successful invoice."""
        result = InvoiceResult(
            success=True,
            invoice_id="inv_123",
            payment_url="https://pay.example.com/123"
        )
        assert result.success is True
        assert result.invoice_id == "inv_123"
        assert result.error is None

    def test_invoice_result_failure(self):
        """Test InvoiceResult with failed invoice."""
        result = InvoiceResult(
            success=False,
            error="API error: 500"
        )
        assert result.success is False
        assert result.error == "API error: 500"
        assert result.invoice_id is None


class TestPaymentCheckResult:
    """Tests for PaymentCheckResult dataclass."""

    def test_payment_check_result_paid(self):
        """Test PaymentCheckResult for paid payment."""
        result = PaymentCheckResult(
            is_paid=True,
            status=PaymentStatus.COMPLETED
        )
        assert result.is_paid is True
        assert result.status == PaymentStatus.COMPLETED

    def test_payment_check_result_pending(self):
        """Test PaymentCheckResult for pending payment."""
        result = PaymentCheckResult(
            is_paid=False,
            status=PaymentStatus.PENDING
        )
        assert result.is_paid is False
        assert result.status == PaymentStatus.PENDING