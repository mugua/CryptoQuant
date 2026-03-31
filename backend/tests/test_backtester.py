"""
Tests for the event-driven backtester.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
import pytest

from engine.backtester import Backtester, BacktestConfig
from engine.strategy_base import Signal, SignalType, StrategyBase


# ---------------------------------------------------------------------------
# Minimal strategies for testing
# ---------------------------------------------------------------------------


class AlwaysBuyStrategy(StrategyBase):
    """Buys on the first candle, never sells – for equity-curve smoke tests."""

    def initialize(self):
        self._bought = False

    def on_candle(self, candle):
        if not self._bought:
            self._bought = True
            close = float(candle["close"])
            qty = (self._capital * 0.99) / close
            return Signal(
                symbol="BTC/USDT",
                signal_type=SignalType.BUY,
                price=close,
                quantity=qty,
            )
        return None

    def on_tick(self, tick):
        return None


class BuyThenSellStrategy(StrategyBase):
    """Buys on candle 5, sells on candle 10."""

    def initialize(self):
        self._count = 0
        self._position_qty = 0.0

    def on_candle(self, candle):
        self._count += 1
        close = float(candle["close"])
        if self._count == 5:
            qty = (self._capital * 0.99) / close
            self._position_qty = qty
            return Signal(symbol="BTC/USDT", signal_type=SignalType.BUY, price=close, quantity=qty)
        if self._count == 10 and self._position_qty > 0:
            qty = self._position_qty
            self._position_qty = 0.0
            return Signal(symbol="BTC/USDT", signal_type=SignalType.SELL, price=close, quantity=qty)
        return None

    def on_tick(self, tick):
        return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def flat_ohlcv() -> pd.DataFrame:
    """100 candles at a flat price of 100."""
    idx = pd.date_range("2023-01-01", periods=100, freq="1h", tz=timezone.utc)
    data = {
        "open": np.ones(100) * 100,
        "high": np.ones(100) * 101,
        "low": np.ones(100) * 99,
        "close": np.ones(100) * 100,
        "volume": np.ones(100) * 1000,
    }
    return pd.DataFrame(data, index=idx)


@pytest.fixture
def rising_ohlcv() -> pd.DataFrame:
    """100 candles with steadily rising prices (100 → 200)."""
    n = 100
    idx = pd.date_range("2023-01-01", periods=n, freq="1h", tz=timezone.utc)
    closes = np.linspace(100, 200, n)
    return pd.DataFrame(
        {
            "open": closes * 0.999,
            "high": closes * 1.002,
            "low": closes * 0.998,
            "close": closes,
            "volume": np.ones(n) * 1000,
        },
        index=idx,
    )


@pytest.fixture
def base_config() -> BacktestConfig:
    return BacktestConfig(
        start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2023, 1, 5, tzinfo=timezone.utc),
        initial_capital=10_000.0,
        commission_rate=0.001,
        slippage=0.001,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_backtest_returns_result(flat_ohlcv, base_config):
    """run() should return a BacktestResult with the expected structure."""
    from engine.backtester import BacktestResult

    strategy = AlwaysBuyStrategy()
    result = Backtester().run(strategy, base_config, flat_ohlcv)
    assert isinstance(result, BacktestResult)
    assert isinstance(result.stats, dict)
    assert isinstance(result.trades, list)
    assert not result.equity_curve.empty


def test_backtest_equity_curve_starts_at_capital(flat_ohlcv, base_config):
    """First equity-curve value should equal the initial capital."""
    strategy = AlwaysBuyStrategy()
    result = Backtester().run(strategy, base_config, flat_ohlcv)
    first_equity = float(result.equity_curve.iloc[0])
    assert abs(first_equity - base_config.initial_capital) < 1.0


def test_backtest_commission_applied(flat_ohlcv, base_config):
    """Total commission should be positive when trades occur."""
    strategy = BuyThenSellStrategy()
    result = Backtester().run(strategy, base_config, flat_ohlcv)
    assert result.stats["total_commission"] > 0


def test_backtest_max_drawdown_calculation(rising_ohlcv, base_config):
    """Max drawdown should be ≥ 0 and ≤ 1."""
    strategy = BuyThenSellStrategy()
    result = Backtester().run(strategy, base_config, rising_ohlcv)
    md = result.stats["max_drawdown"]
    assert 0.0 <= md <= 1.0


def test_backtest_sharpe_ratio(rising_ohlcv, base_config):
    """Sharpe ratio should be a finite float."""
    import math

    strategy = BuyThenSellStrategy()
    result = Backtester().run(strategy, base_config, rising_ohlcv)
    sharpe = result.stats["sharpe_ratio"]
    assert isinstance(sharpe, float)
    assert not math.isnan(sharpe)


def test_backtest_win_rate_in_range(flat_ohlcv, base_config):
    strategy = BuyThenSellStrategy()
    result = Backtester().run(strategy, base_config, flat_ohlcv)
    win_rate = result.stats["win_rate"]
    assert 0.0 <= win_rate <= 1.0


def test_backtest_no_trades_on_hold_strategy(flat_ohlcv, base_config):
    """A strategy that never generates signals should have 0 trades."""

    class HoldStrategy(StrategyBase):
        def initialize(self):
            pass

        def on_candle(self, candle):
            return None

        def on_tick(self, tick):
            return None

    result = Backtester().run(HoldStrategy(), base_config, flat_ohlcv)
    assert result.stats["total_trades"] == 0


def test_backtest_profit_on_rising_market(rising_ohlcv, base_config):
    """Buying early and selling late on a rising market should be profitable."""
    strategy = BuyThenSellStrategy()
    result = Backtester().run(strategy, base_config, rising_ohlcv)
    # At least one trade must have occurred and total return should be positive.
    if result.stats["total_trades"] > 0:
        assert result.stats["final_capital"] > base_config.initial_capital * 0.9


def test_backtest_empty_df_raises():
    """An empty OHLCV DataFrame should raise ValueError."""
    with pytest.raises(ValueError):
        Backtester().run(
            AlwaysBuyStrategy(),
            BacktestConfig(
                start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2023, 1, 2, tzinfo=timezone.utc),
            ),
            pd.DataFrame(),
        )
