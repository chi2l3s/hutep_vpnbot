"""Модели базы данных для HutepVPN бота."""

from datetime import datetime
import random
import string

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ─────────────────────────────────────────────────────────────
# Базовый класс
# ─────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


# ─────────────────────────────────────────────────────────────
# Модели
# ─────────────────────────────────────────────────────────────

class User(Base):
    """Пользователь Telegram."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    referral_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    referred_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    vpn_client_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    subscription: Mapped["Subscription | None"] = relationship(
        "Subscription", back_populates="user", uselist=False
    )
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="user")
    referrals: Mapped[list["User"]] = relationship(
        "User", backref="referrer", remote_side=[id]
    )

    @staticmethod
    def generate_referral_code() -> str:
        chars = string.ascii_uppercase + string.digits
        return "HV-" + "".join(random.choices(chars, k=6))


class Subscription(Base):
    """Подписка пользователя."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="subscription")

    @property
    def is_valid(self) -> bool:
        return self.is_active and self.end_date > datetime.utcnow()

    @property
    def days_remaining(self) -> int:
        if not self.is_valid:
            return 0
        delta = self.end_date - datetime.utcnow()
        return max(0, delta.days)


class Payment(Base):
    """Платёж пользователя."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    amount_stars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False)
    payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    invoice_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    crypto_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    crypto_amount: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="payments")

    def to_stars_amount(self) -> int:
        if self.amount_stars is not None:
            return self.amount_stars
        return int(self.amount / 0.2)


class VPNProfile(Base):
    """VPN профиль пользоваанта."""

    __tablename__ = "vpn_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    protocol: Mapped[str] = mapped_column(String(20), nullable=False)
    profile_uuid: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    sub_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    profile_link: Mapped[str] = mapped_column(Text, nullable=False)
    server_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", backref="vpn_profiles")


# ─────────────────────────────────────────────────────────────
# Подключение к БД
# ─────────────────────────────────────────────────────────────

_engine = None
_async_session_maker = None


def get_database_url() -> str:
    """Получение URL базы данных (отложенный импорт, чтобы избежать циркулярной зависимости)."""
    from bot.config import settings
    return settings.database_url


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            get_database_url(),
            echo=False,
            future=True,
        )
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    global _async_session_maker
    if _async_session_maker is None:
        engine = get_engine()
        _async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_maker


async def get_session() -> AsyncSession:
    session_maker = get_session_maker()
    async with session_maker() as session:
        yield session


async def init_db() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    global _engine, _async_session_maker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_maker = None