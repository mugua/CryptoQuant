"""
Tests for trading strategies.

All tests use synthetic in-memory OHLCV DataFrames so no external data or
exchange connections are needed.
"""

from __future__ import annotations

from datetime import timezone

import numpy as np
import pandas as pd
import pytest

from engine.strategy_base import SignalType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ohlcv(closes: list, n: int = None) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame from a close-price list."""
    if n is not None:
        closes = closes[:n]
    closes_arr = np.array(closes, dtype=float)
    highs = closes_arr * 1.01
    lows = closes_arr * 0.99
    opens = np.roll(closes_arr, 1)
    opens[0] = closes_arr[0]
    volumes = np.ones(len(closes_arr)) * 1000
    idx = pd.date_range("2023-01-01", periods=len(closes_arr), freq="1h", tz=timezone.utc)
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes_arr, "volume": volumes},
        index=idx,
    )


def _run_strategy(strategy, df: pd.DataFrame):
    """Run a strategy over a full OHLCV DataFrame, returning all signals."""
    strategy.initialize()
    signals = []
    for _, row in df.iterrows():
        sig = strategy.on_candle(row)
        if sig is not None:
            signals.append(sig)
    return signals


# ---------------------------------------------------------------------------
# MovingAverageCross
# ---------------------------------------------------------------------------


def test_ma_cross_buy_signal():
    """
    A golden cross (fast MA crosses above slow MA) should produce a BUY signal.
    Generate prices that go from falling → rising to create a definitive cross.
    """
    from strategies.moving_average_cross import MovingAverageCross

    # 50 bars: first 25 falling, then 25 strongly rising → creates a crossover.
    falling = np.linspace(200, 150, 25)
    rising = np.linspace(150, 300, 25)
    closes = list(falling) + list(rising)
    df = _make_ohlcv(closes)

    strategy = MovingAverageCross(
        parameters={"fast_period": 5, "slow_period": 15, "symbol": "BTC/USDT"}
    )
    strategy._set_capital(10_000.0)
    signals = _run_strategy(strategy, df)

    buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
    assert len(buy_signals) >= 1


def test_ma_cross_sell_signal():
    """
    A death cross (fast MA crosses below slow MA) should produce a SELL signal.
    """
    from strategies.moving_average_cross import MovingAverageCross

    # Rising then sharply falling to force a death cross.
    rising = np.linspace(100, 200, 25)
    falling = np.linspace(200, 80, 25)
    closes = list(rising) + list(falling)
    df = _make_ohlcv(closes)

    strategy = MovingAverageCross(
        parameters={"fast_period": 5, "slow_period": 15, "symbol": "BTC/USDT"}
    )
    strategy._set_capital(10_000.0)

    # Manually inject a position so the strategy can sell.
    strategy.initialize()
    strategy._positions["BTC/USDT"] = __import__(
        "engine.strategy_base", fromlist=["Position"]
    ).Position(symbol="BTC/USDT", quantity=0.1, avg_entry_price=150.0)

    signals = []
    for _, row in df.iterrows():
        sig = strategy.on_candle(row)
        if sig is not None:
            signals.append(sig)

    sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
    assert len(sell_signals) >= 1


# ---------------------------------------------------------------------------
# RSIStrategy
# ---------------------------------------------------------------------------


def test_rsi_oversold_buy():
    """RSI falling below 30 should trigger a BUY signal."""
    from strategies.rsi_strategy import RSIStrategy

    # Create a strongly declining series to push RSI into oversold territory.
    closes = list(np.linspace(200, 80, 60))  # steep decline
    df = _make_ohlcv(closes)

    strategy = RSIStrategy(
        parameters={"rsi_period": 14, "oversold": 30, "overbought": 70, "symbol": "BTC/USDT"}
    )
    strategy._set_capital(10_000.0)
    signals = _run_strategy(strategy, df)

    buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
    assert len(buy_signals) >= 1


def test_rsi_overbought_sell():
    """RSI rising above 70 while in a position should trigger a SELL signal."""
    from strategies.rsi_strategy import RSIStrategy
    from engine.strategy_base import Position

    # Strongly rising series to push RSI into overbought.
    closes = list(np.linspace(100, 300, 60))
    df = _make_ohlcv(closes)

    strategy = RSIStrategy(
        parameters={"rsi_period": 14, "oversold": 30, "overbought": 70, "symbol": "BTC/USDT"}
    )
    strategy._set_capital(10_000.0)
    strategy.initialize()
    # Manually inject a long position.
    strategy._positions["BTC/USDT"] = Position(symbol="BTC/USDT", quantity=0.05, avg_entry_price=100.0)

    signals = []
    for _, row in df.iterrows():
        sig = strategy.on_candle(row)
        if sig is not None:
            signals.append(sig)

    sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
    assert len(sell_signals) >= 1


def test_rsi_midline_exit():
    """RSI crossing the midline (50) from below should close a long position."""
    from strategies.rsi_strategy import RSIStrategy
    from engine.strategy_base import Position

    # First decline then rise through midline.
    declining = list(np.linspace(200, 120, 30))
    recovering = list(np.linspace(120, 200, 30))
    closes = declining + recovering
    df = _make_ohlcv(closes)

    strategy = RSIStrategy(
        parameters={
            "rsi_period": 14,
            "oversold": 30,
            "overbought": 80,
            "exit_rsi_buy": 50,
            "symbol": "BTC/USDT",
        }
    )
    strategy._set_capital(10_000.0)
    strategy.initialize()
    strategy._positions["BTC/USDT"] = Position(symbol="BTC/USDT", quantity=0.05, avg_entry_price=130.0)
    strategy._prev_rsi = 40.0  # set up for midline crossing

    signals = []
    for _, row in df.iterrows():
        sig = strategy.on_candle(row)
        if sig is not None:
            signals.append(sig)

    sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
    # At least one sell should fire during the recovery.
    assert len(sell_signals) >= 1


# ---------------------------------------------------------------------------
# BollingerBandsStrategy
# ---------------------------------------------------------------------------


def test_bollinger_bands_entry():
    """Price touching the lower band during a squeeze should trigger a BUY."""
    from strategies.bollinger_bands import BollingerBandsStrategy

    # Flat price with a single dip to force a lower-band touch + squeeze.
    np.random.seed(0)
    base = 100.0
    # Tight sideways movement (squeeze) then a dip.
    tight = [base + np.random.normal(0, 0.5) for _ in range(30)]
    dip = [base * 0.93] * 5  # strong dip below lower band
    closes = tight + dip + tight

    df = _make_ohlcv(closes)

    strategy = BollingerBandsStrategy(
        parameters={
            "period": 20,
            "std_dev": 2.0,
            "squeeze_threshold": 0.10,
            "symbol": "BTC/USDT",
        }
    )
    strategy._set_capital(10_000.0)
    signals = _run_strategy(strategy, df)

    buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
    # The dip should have triggered at least one buy.
    assert len(buy_signals) >= 1


def test_bollinger_bands_upper_band_exit():
    """Holding a position and price touching the upper band should trigger a SELL."""
    from strategies.bollinger_bands import BollingerBandsStrategy
    from engine.strategy_base import Position

    np.random.seed(1)
    base = 100.0
    tight = [base + np.random.normal(0, 0.5) for _ in range(25)]
    surge = [base * 1.10] * 5  # push to upper band
    closes = tight + surge

    df = _make_ohlcv(closes)

    strategy = BollingerBandsStrategy(
        parameters={"period": 20, "std_dev": 2.0, "squeeze_threshold": 0.5, "symbol": "BTC/USDT"}
    )
    strategy._set_capital(10_000.0)
    strategy.initialize()
    strategy._positions["BTC/USDT"] = Position(symbol="BTC/USDT", quantity=0.1, avg_entry_price=95.0)
    strategy._stop_loss_price = 99.0

    signals = []
    for _, row in df.iterrows():
        sig = strategy.on_candle(row)
        if sig is not None:
            signals.append(sig)

    sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
    assert len(sell_signals) >= 1
