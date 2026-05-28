"""Конфигурация бота HutepVPN."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # === Telegram ===
    bot_token: str = ""

    # === X-UI ===
    xui_api_url: str = "http://localhost:20561"
    xui_api_key: str = ""
    xui_use_tls: bool = False

    # === База данных ===
    database_url: str = "sqlite+aiosqlite:///./data/hutep_vpn.db"

    # === NOWPayments ===
    nowpayments_api_key: str = ""
    nowpayments_webhook_secret: str = ""
    nowpayments_sandbox: bool = False

    # === Реферальная система ===
    referral_bonus_days: int = 7

    # === Администраторы (строка через запятую) ===
    admin_ids: str = ""

    # === Веб-сервер ===
    webhook_host: str = ""
    webhook_path: str = "/webhook"
    webapp_host: str = "0.0.0.0"
    webapp_port: int = 8080

    # === Прокси ===
    proxy: str = ""

    # === VPN Subscription ===
    subscription_domain: str = "https://vpn.mylumina.ru:2096"

    @property
    def db_path(self) -> Path:
        """Путь к файлу базы данных."""
        return Path("data/hutep_vpn.db")

    @property
    def admin_list(self) -> list[int]:
        """Список ID администраторов."""
        if not self.admin_ids:
            return []
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip().isdigit()]

    @property
    def subscription_plans(self) -> dict:
        """Тарифные планы подписок."""
        return {
            30: {"price": 70, "days": 30, "name": "Базовая подписка"},
            90: {"price": 190, "days": 90, "name": "Выгодная подписка"},
            180: {"price": 350, "days": 180, "name": "Премиум подписка"},
            360: {"price": 600, "days": 360, "name": "Годовая подписка"},
        }


# Глобальный экземпляр настроек
settings = Settings()