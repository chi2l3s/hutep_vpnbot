"""Shared pytest fixtures."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_user():
    """Create a mock User object."""
    user = MagicMock()
    user.id = 123456789
    user.username = "testuser"
    user.full_name = "Test User"
    user.referral_code = "HV-TEST01"
    user.referred_by = None
    user.vpn_client_email = None
    user.created_at = datetime.utcnow()
    return user


@pytest.fixture
def mock_subscription_active():
    """Create a mock active Subscription object."""
    sub = MagicMock()
    sub.id = 1
    sub.user_id = 123456789
    sub.days = 30
    sub.start_date = datetime.utcnow()
    sub.end_date = datetime.utcnow() + timedelta(days=30)
    sub.is_active = True
    sub.is_valid = True
    sub.days_remaining = 30
    return sub


@pytest.fixture
def mock_subscription_expired():
    """Create a mock expired Subscription object."""
    sub = MagicMock()
    sub.id = 2
    sub.user_id = 987654321
    sub.days = 30
    sub.start_date = datetime.utcnow() - timedelta(days=60)
    sub.end_date = datetime.utcnow() - timedelta(days=30)
    sub.is_active = True
    sub.is_valid = False
    sub.days_remaining = 0
    return sub


@pytest.fixture
def mock_vpn_profile():
    """Create a mock VPNProfile object."""
    profile = MagicMock()
    profile.id = 1
    profile.user_id = 123456789
    profile.protocol = "vless"
    profile.profile_uuid = "test-uuid-1234"
    profile.sub_id = "sub123"
    profile.profile_link = "https://vpn.example.com/sub/sub123"
    profile.server_name = "HutepVPN Server"
    profile.is_active = True
    profile.created_at = datetime.utcnow()
    return profile


@pytest.fixture
def mock_payment():
    """Create a mock Payment object."""
    payment = MagicMock()
    payment.id = 1
    payment.user_id = 123456789
    payment.amount = 70.0
    payment.amount_stars = 56
    payment.days = 30
    payment.status = "pending"
    payment.payment_method = "stars"
    payment.payment_id = None
    payment.invoice_id = "inv_123"
    payment.crypto_address = None
    payment.crypto_amount = None
    payment.created_at = datetime.utcnow()
    return payment


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession object."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.get = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_xui_response():
    """Create a mock X-UI API response."""
    return {
        "success": True,
        "obj": {
            "id": "client-uuid-123",
            "email": "123456789",
            "subId": "sub123",
            "enable": True,
            "flow": "xtls-rprx-vision",
        }
    }