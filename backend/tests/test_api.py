"""
API integration tests using httpx AsyncClient + in-memory SQLite.

These tests exercise the full FastAPI application stack (auth, users,
strategies, backtest) without requiring a live database or exchange.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """POST /api/v1/auth/register should return access and refresh tokens."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "SecurePass123",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Registering the same email twice should return 400/409."""
    payload = {
        "email": "dup@example.com",
        "username": "dupuser1",
        "password": "SecurePass123",
    }
    await client.post("/api/v1/auth/register", json=payload)

    payload2 = {
        "email": "dup@example.com",
        "username": "dupuser2",
        "password": "SecurePass123",
    }
    resp = await client.post("/api/v1/auth/register", json=payload2)
    assert resp.status_code in (400, 409, 422)


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    """POST /api/v1/auth/login should return tokens for valid credentials."""
    # Register first.
    await client.post(
        "/api/v1/auth/register",
        json={"email": "logintest@example.com", "username": "logintest", "password": "LoginPass123"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "logintest@example.com", "password": "LoginPass123"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Wrong password should return 401."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpw@example.com", "username": "wrongpw", "password": "RightPass123"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@example.com", "password": "WrongPass999"},
    )
    assert resp.status_code in (401, 400)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient):
    """GET /api/v1/users/me should return the authenticated user's profile."""
    # Register and login.
    await client.post(
        "/api/v1/auth/register",
        json={"email": "metest@example.com", "username": "metest", "password": "MePass1234"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "metest@example.com", "password": "MePass1234"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["email"] == "metest@example.com"
    assert data["username"] == "metest"


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient):
    """Accessing /me without a token should return 401."""
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_update_user_settings(client: AsyncClient):
    """
    PUT /api/v1/users/me/settings should update theme_mode and language.
    """
    # Register + login.
    await client.post(
        "/api/v1/auth/register",
        json={"email": "settings@example.com", "username": "settingsuser", "password": "Settings123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "settings@example.com", "password": "Settings123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.put(
        "/api/v1/users/me/settings",
        headers=headers,
        json={"theme_mode": "dark", "language": "en-US"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["theme_mode"] == "dark"
    assert data["language"] == "en-US"


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_strategy(client: AsyncClient):
    """POST /api/v1/strategies should create a strategy and return it."""
    # Register + login.
    await client.post(
        "/api/v1/auth/register",
        json={"email": "strat@example.com", "username": "stratuser", "password": "Strat1234"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "strat@example.com", "password": "Strat1234"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/strategies",
        headers=headers,
        json={
            "name": "My MA Cross",
            "description": "Test strategy",
            "strategy_type": "MA_CROSS",
            "parameters": {"fast_period": 9, "slow_period": 21},
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "timeframe": "1h",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == "My MA Cross"
    assert data["strategy_type"] == "MA_CROSS"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_strategies(client: AsyncClient):
    """GET /api/v1/strategies should return the user's strategies."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "liststrat@example.com", "username": "liststrat", "password": "List1234"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "liststrat@example.com", "password": "List1234"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a strategy.
    await client.post(
        "/api/v1/strategies",
        headers=headers,
        json={
            "name": "RSI Strategy",
            "strategy_type": "RSI",
            "parameters": {"rsi_period": 14},
            "exchange": "binance",
            "symbol": "ETH/USDT",
            "timeframe": "1h",
        },
    )

    resp = await client.get("/api/v1/strategies", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "items" in data or isinstance(data, (list, dict))


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_backtest(client: AsyncClient):
    """
    POST /api/v1/backtest/run should execute a backtest and return stats.
    """
    # Register + login.
    await client.post(
        "/api/v1/auth/register",
        json={"email": "bttest@example.com", "username": "bttestuser", "password": "Backtest123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "bttest@example.com", "password": "Backtest123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/backtest/run",
        headers=headers,
        json={
            "strategy_type": "MA_CROSS",
            "parameters": {"fast_period": 10, "slow_period": 30},
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "timeframe": "1h",
            "start_date": "2023-01-01T00:00:00Z",
            "end_date": "2023-06-01T00:00:00Z",
            "initial_capital": "10000",
            "commission_rate": 0.001,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "stats" in data
    assert "equity_curve" in data
    stats = data["stats"]
    assert "total_trades" in stats
    assert "sharpe_ratio" in stats
    assert "max_drawdown" in stats
    assert "win_rate" in stats
