"""Сервис платежей (Telegram Stars + NOWPayments)."""

import hashlib
import hmac
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

import aiohttp

from bot.config import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Типы платежей
# ─────────────────────────────────────────────────────────────

class PaymentMethod(Enum):
    """Способ оплаты."""
    STARS = "stars"
    CRYPTO = "crypto"


class PaymentStatus(Enum):
    """Статус платежа."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass
class InvoiceResult:
    """Результат создания инвойса."""
    success: bool
    invoice_id: str | None = None
    payment_url: str | None = None
    crypto_address: str | None = None
    crypto_amount: str | None = None
    error: str | None = None


@dataclass
class PaymentCheckResult:
    """Результат проверки платежа."""
    is_paid: bool
    status: PaymentStatus
    error: str | None = None


# ─────────────────────────────────────────────────────────────
# Базовый класс провайдера платежей
# ─────────────────────────────────────────────────────────────

class PaymentProvider(ABC):
    """Абстрактный класс провайдера платежей."""

    @abstractmethod
    async def create_invoice(
        self,
        amount: float,
        days: int,
        user_telegram_id: int,
    ) -> InvoiceResult:
        """Создать инвойс для оплаты."""
        pass

    @abstractmethod
    async def check_payment(self, invoice_id: str) -> PaymentCheckResult:
        """Проверить статус платежа."""
        pass

    @abstractmethod
    async def handle_webhook(self, payload: dict) -> bool:
        """Обработать webhook от платёжной системы."""
        pass


# ─────────────────────────────────────────────────────────────
# NOWPayments провайдер
# ─────────────────────────────────────────────────────────────

class NOWPaymentsProvider(PaymentProvider):
    """Провайдер платежей через NOWPayments."""

    BASE_URL = "https://api.nowpayments.io/v1"

    def __init__(self) -> None:
        self.api_key = settings.nowpayments_api_key
        self.webhook_secret = settings.nowpayments_webhook_secret
        self.sandbox = settings.nowpayments_sandbox
        self.base_url = self.BASE_URL

        if self.sandbox:
            self.base_url = "https://api.nowpayments.io/v1"

    def _get_headers(self) -> dict:
        """Заголовки для запросов к NOWPayments."""
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

    async def create_invoice(
        self,
        amount: float,
        days: int,
        user_telegram_id: int,
    ) -> InvoiceResult:
        """Создание платёжной ссылки через NOWPayments."""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "price_amount": amount,
                    "price_currency": "rub",
                    "order_id": f"hv_{user_telegram_id}_{uuid.uuid4().hex[:8]}",
                    "order_description": f"HutepVPN {days} дней",
                    "is_fee_paid_by_user": False,
                    "success_url": "https://t.me/",
                }

                # Добавляем webhook только если настроен публичный URL
                if settings.webhook_host:
                    payload["ipn_callback_url"] = f"{settings.webhook_host}/webhook/nowpayments"

                async with session.post(
                    f"{self.base_url}/invoice",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        logger.error(f"NOWPayments invoice error: {response.status} - {text}")
                        return InvoiceResult(
                            success=False,
                            error=f"API error: {response.status}",
                        )

                    data = await response.json()

                    return InvoiceResult(
                        success=True,
                        invoice_id=data.get("id"),
                        payment_url=data.get("invoice_url"),
                    )

        except aiohttp.ClientError as e:
            logger.error(f"NOWPayments connection error: {e}")
            return InvoiceResult(success=False, error=str(e))

    async def check_payment(self, invoice_id: str) -> PaymentCheckResult:
        """Проверка статуса платежа через NOWPayments."""
        return PaymentCheckResult(is_paid=False, status=PaymentStatus.PENDING)

    async def handle_webhook(self, payload: dict) -> bool:
        """
        Обработка webhook от NOWPayments.

        Пример payload:
        {
            "id": "...",
            "order_id": "hv_12345_abc123",
            "payment_status": "finished",
            "price_amount": 70,
            "price_currency": "rub",
            "pay_address": "...",
            ...
        }
        """
        try:
            # Проверяем подпись webhook
            if self.webhook_secret:
                signature = hmac.new(
                    self.webhook_secret.encode(),
                    str(payload).encode(),
                    hashlib.sha256,
                ).hexdigest()
                # NOWPayments может отправлять подпись в заголовке
                # x-nowpayments-sig

            payment_status = payload.get("payment_status", "")
            order_id = payload.get("order_id", "")

            # Из order_id извлекаем telegram_id
            # format: hv_{telegram_id}_{random}
            if order_id.startswith("hv_"):
                parts = order_id.split("_")
                if len(parts) >= 2:
                    return payment_status in ("finished", "confirmed")

            return False

        except Exception as e:
            logger.error(f"NOWPayments webhook error: {e}")
            return False

    async def get_payment_status(self, payment_id: str) -> PaymentCheckResult:
        """Получение статуса платежа."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/payment/{payment_id}",
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status != 200:
                        return PaymentCheckResult(
                            is_paid=False,
                            status=PaymentStatus.FAILED,
                            error=f"API error: {response.status}",
                        )

                    data = await response.json()
                    payment_status = data.get("payment_status", "")

                    if payment_status in ("finished", "confirmed"):
                        return PaymentCheckResult(
                            is_paid=True,
                            status=PaymentStatus.COMPLETED,
                        )
                    elif payment_status in ("expired", "failed"):
                        return PaymentCheckResult(
                            is_paid=False,
                            status=PaymentStatus.FAILED,
                        )
                    else:
                        return PaymentCheckResult(
                            is_paid=False,
                            status=PaymentStatus.PENDING,
                        )

        except aiohttp.ClientError as e:
            logger.error(f"NOWPayments check error: {e}")
            return PaymentCheckResult(
                is_paid=False,
                status=PaymentStatus.PENDING,
                error=str(e),
            )


# ─────────────────────────────────────────────────────────────
# Менеджер платежей
# ─────────────────────────────────────────────────────────────

class PaymentService:
    """Управление платежами через разные провайдеры."""

    def __init__(self) -> None:
        self.crypto_provider = NOWPaymentsProvider()

    def calculate_stars_amount(self, amount_rub: float) -> int:
        """
        Конвертация рублей в Telegram Stars.

        1 Star ≈ 0.2 рубля (примерный курс, можно настроить)
        """
        return max(1, int(amount_rub / 0.2))

    async def create_stars_invoice(
        self,
        amount_rub: float,
        days: int,
        title: str,
    ) -> dict:
        """
        Создание данных для оплаты через Telegram Stars.

        Возвращает словарь с данными для send_invoice.
        """
        stars_amount = self.calculate_stars_amount(amount_rub)

        return {
            "title": title,
            "description": f"Подписка HutepVPN на {days} дней",
            "payload": f"sub_{days}_{stars_amount}",
            "provider_token": "",  # Для Stars токен не нужен
            "currency": "XTR",
            "prices": [{"label": f"{days} дней подписки", "amount": stars_amount}],
        }

    async def create_crypto_invoice(
        self,
        amount: float,
        days: int,
        user_telegram_id: int,
    ) -> InvoiceResult:
        """Создание крипто-инвойса через NOWPayments."""
        return await self.crypto_provider.create_invoice(
            amount=amount,
            days=days,
            user_telegram_id=user_telegram_id,
        )

    async def check_crypto_payment(self, invoice_id: str) -> PaymentCheckResult:
        """Проверка крипто-платежа."""
        return await self.crypto_provider.get_payment_status(invoice_id)

    async def handle_nowpayments_webhook(self, payload: dict) -> bool:
        """Обработка webhook от NOWPayments."""
        return await self.crypto_provider.handle_webhook(payload)


# Глобальный экземпляр
_payment_service: PaymentService | None = None


def get_payment_service() -> PaymentService:
    """Получение экземпляра сервиса платежей."""
    global _payment_service
    if _payment_service is None:
        _payment_service = PaymentService()
    return _payment_service