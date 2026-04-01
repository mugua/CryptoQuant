"""
pytest fixtures shared across the test suite.

Database and HTTP client fixtures use in-memory SQLite (via aiosqlite) so
no PostgreSQL instance is required during CI.
"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import get_db
from app.models.base import BaseModel
from app.models.user import User
from app.models.strategy import Strategy
from app.core.security import get_password_hash

# ---------------------------------------------------------------------------
# In-memory SQLite engine (no Postgres needed)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Session-scoped event loop
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def event_loop():
    """Provide a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Database setup / teardown
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once per test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a per-test transactional database session."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# FastAPI dependency override
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with the DB dependency overridden."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Sample fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """Create and persist a sample active user."""
    import uuid

    user = User(
        id=uuid.uuid4(),
        email="testuser@example.com",
        username="testuser",
        hashed_password=get_password_hash("TestPassword123"),
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_strategy(db_session: AsyncSession, sample_user: User) -> Strategy:
    """Create and persist a sample strategy owned by *sample_user*."""
    import uuid

    strategy = Strategy(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        name="Test MA Cross",
        description="Test strategy",
        strategy_type="MA_CROSS",
        parameters={"fast_period": 9, "slow_period": 21},
        is_active=True,
        is_running=False,
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
    )
    db_session.add(strategy)
    await db_session.commit()
    await db_session.refresh(strategy)
    return strategy


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, sample_user: User) -> dict:
    """Return Authorization headers for *sample_user*."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": sample_user.email, "password": "TestPassword123"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
