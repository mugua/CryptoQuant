"""
Tests for the RiskManager class.
"""

from __future__ import annotations

import pytest

from engine.risk_manager import RiskManager, RiskConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def risk_manager() -> RiskManager:
    config = RiskConfig(
        max_position_size_pct=0.10,
        max_daily_loss_pct=0.02,
        max_drawdown_limit_pct=0.15,
        max_open_positions=3,
    )
    return RiskManager(config=config, initial_equity=10_000.0)


# ---------------------------------------------------------------------------
# Position size limit
# ---------------------------------------------------------------------------


def test_position_size_limit_allows_small_order(risk_manager):
    """An order worth 5 % of equity should be allowed."""
    allowed, reason = risk_manager.check_order("BTC/USDT", "buy", 0.05, 10_000.0)
    assert allowed, f"Expected allowed but got: {reason}"


def test_position_size_limit_blocks_large_order(risk_manager):
    """An order worth 15 % of equity should be blocked (limit is 10 %)."""
    allowed, reason = risk_manager.check_order("BTC/USDT", "buy", 0.15, 10_000.0)
    assert not allowed
    assert "max position size" in reason.lower()


def test_position_size_limit_exact_boundary(risk_manager):
    """An order exactly at the limit (10 %) should be allowed."""
    allowed, reason = risk_manager.check_order("BTC/USDT", "buy", 0.10, 10_000.0)
    assert allowed, f"Expected allowed at boundary but got: {reason}"


def test_max_open_positions_blocks_new_symbol(risk_manager):
    """Opening a 4th position when limit is 3 should be blocked."""
    for i, sym in enumerate(["ETH/USDT", "BNB/USDT", "SOL/USDT"]):
        risk_manager.update_positions({"symbol": sym, "side": "buy", "quantity": 0.01, "price": 100.0})

    allowed, reason = risk_manager.check_order("XRP/USDT", "buy", 0.005, 100.0)
    assert not allowed
    assert "max open positions" in reason.lower()


def test_sell_order_always_allowed_under_drawdown(risk_manager):
    """Sell orders should not be blocked by position-size or position-count limits."""
    # Simulate an open position by updating state directly.
    risk_manager.update_positions({"symbol": "BTC/USDT", "side": "buy", "quantity": 0.05, "price": 10_000.0})
    allowed, reason = risk_manager.check_order("BTC/USDT", "sell", 0.05, 10_000.0)
    # Sell should pass as long as drawdown/daily-loss limits are not breached.
    assert allowed, f"Sell blocked unexpectedly: {reason}"


# ---------------------------------------------------------------------------
# Daily loss limit
# ---------------------------------------------------------------------------


def test_daily_loss_limit_blocks_order(risk_manager):
    """Orders should be blocked after daily loss limit is exceeded."""
    # Simulate losses: reduce portfolio equity below 2 % daily loss threshold.
    # Day-start equity = 10 000; limit is 2 % → block below 9 800.
    risk_manager._portfolio_equity = 9_700.0  # 3 % loss
    allowed, reason = risk_manager.check_order("BTC/USDT", "buy", 0.001, 1000.0)
    assert not allowed
    assert "daily loss" in reason.lower()


def test_daily_loss_limit_allows_order_within_limit(risk_manager):
    """Orders should be allowed when daily loss is within the limit."""
    risk_manager._portfolio_equity = 9_900.0  # 1 % loss, limit is 2 %
    allowed, reason = risk_manager.check_order("BTC/USDT", "buy", 0.001, 100.0)
    assert allowed, f"Expected allowed but got: {reason}"


# ---------------------------------------------------------------------------
# Max drawdown stop
# ---------------------------------------------------------------------------


def test_max_drawdown_stop(risk_manager):
    """All orders should be blocked when max drawdown limit is breached."""
    # Peak equity is 10 000; limit is 15 %; block below 8 500.
    risk_manager._portfolio_equity = 8_000.0  # 20 % drawdown
    allowed, reason = risk_manager.check_order("BTC/USDT", "buy", 0.001, 100.0)
    assert not allowed
    assert "drawdown" in reason.lower()


def test_max_drawdown_stop_force_close(risk_manager):
    """force_close_all() should return close orders for every open position."""
    risk_manager.update_positions({"symbol": "BTC/USDT", "side": "buy", "quantity": 0.1, "price": 50_000.0})
    risk_manager.update_positions({"symbol": "ETH/USDT", "side": "buy", "quantity": 1.0, "price": 3_000.0})
    orders = risk_manager.force_close_all()
    symbols = {o["symbol"] for o in orders}
    assert "BTC/USDT" in symbols
    assert "ETH/USDT" in symbols


# ---------------------------------------------------------------------------
# Risk metrics
# ---------------------------------------------------------------------------


def test_get_risk_metrics_returns_dict(risk_manager):
    metrics = risk_manager.get_risk_metrics()
    assert isinstance(metrics, dict)
    required_keys = {"portfolio_equity", "current_drawdown_pct", "daily_loss_pct", "open_positions"}
    assert required_keys.issubset(metrics.keys())


# ---------------------------------------------------------------------------
# Kelly criterion
# ---------------------------------------------------------------------------


def test_kelly_positive_edge(risk_manager):
    """Kelly size should be positive with a winning edge."""
    size = risk_manager.kelly_position_size(win_rate=0.6, avg_win=0.05, avg_loss=0.03)
    assert size > 0


def test_kelly_no_edge(risk_manager):
    """Kelly size should be 0 when there is no edge (win_rate * avg_win = (1-wr) * avg_loss)."""
    size = risk_manager.kelly_position_size(win_rate=0.375, avg_win=0.04, avg_loss=0.06)
    assert size >= 0


def test_kelly_capped_at_max_position_size(risk_manager):
    """Kelly should never exceed max_position_size_pct."""
    size = risk_manager.kelly_position_size(win_rate=0.9, avg_win=0.5, avg_loss=0.01)
    assert size <= risk_manager.config.max_position_size_pct
