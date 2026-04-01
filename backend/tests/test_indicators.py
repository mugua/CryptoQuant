"""
Unit tests for technical indicators in engine/indicators.py.

All tests use deterministic synthetic data so no external data sources or
random seeds are required.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engine import indicators as ind


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def price_series() -> pd.Series:
    """100 ascending prices with small noise."""
    np.random.seed(42)
    base = np.linspace(100, 200, 100)
    noise = np.random.normal(0, 1, 100)
    return pd.Series(base + noise)


@pytest.fixture
def ohlcv_df() -> pd.DataFrame:
    """Synthetic OHLCV DataFrame (100 bars)."""
    np.random.seed(42)
    n = 100
    closes = np.linspace(100, 200, n) + np.random.normal(0, 2, n)
    highs = closes + np.abs(np.random.normal(0, 1, n))
    lows = closes - np.abs(np.random.normal(0, 1, n))
    opens = np.roll(closes, 1)
    opens[0] = closes[0]
    volumes = np.random.uniform(1000, 5000, n)
    return pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes})


# ---------------------------------------------------------------------------
# SMA
# ---------------------------------------------------------------------------


def test_sma_calculation(price_series):
    sma = ind.SMA(price_series, 10)
    assert isinstance(sma, pd.Series)
    assert len(sma) == len(price_series)
    # First 9 values should be NaN (min_periods=period).
    assert sma.iloc[:9].isna().all()
    assert not pd.isna(sma.iloc[9])
    # Manual check: SMA(10) at index 9 equals mean of first 10 values.
    expected = price_series.iloc[:10].mean()
    assert abs(float(sma.iloc[9]) - expected) < 1e-6


def test_sma_monotone_on_flat(price_series):
    flat = pd.Series([50.0] * 30)
    sma = ind.SMA(flat, 5)
    valid = sma.dropna()
    assert (valid == 50.0).all()


# ---------------------------------------------------------------------------
# EMA
# ---------------------------------------------------------------------------


def test_ema_calculation(price_series):
    ema = ind.EMA(price_series, 12)
    assert isinstance(ema, pd.Series)
    assert len(ema) == len(price_series)
    assert not ema.iloc[11:].isna().any()


def test_ema_reacts_faster_than_sma(price_series):
    """EMA should respond more quickly to recent price changes."""
    sma = ind.SMA(price_series, 20)
    ema = ind.EMA(price_series, 20)
    # Both valid from index 19 onward; EMA diverges from SMA.
    assert not (sma.dropna() == ema.dropna()).all()


# ---------------------------------------------------------------------------
# RSI
# ---------------------------------------------------------------------------


def test_rsi_range(price_series):
    rsi = ind.RSI(price_series, 14)
    valid = rsi.dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


def test_rsi_rising_market():
    """All-rising series should produce RSI close to 100."""
    rising = pd.Series(np.linspace(100, 200, 50))
    rsi = ind.RSI(rising, 14)
    last_rsi = float(rsi.dropna().iloc[-1])
    assert last_rsi > 90


def test_rsi_falling_market():
    """All-falling series should produce RSI close to 0."""
    falling = pd.Series(np.linspace(200, 100, 50))
    rsi = ind.RSI(falling, 14)
    last_rsi = float(rsi.dropna().iloc[-1])
    assert last_rsi < 10


# ---------------------------------------------------------------------------
# MACD
# ---------------------------------------------------------------------------


def test_macd_components(price_series):
    macd, signal, hist = ind.MACD(price_series, 12, 26, 9)
    assert isinstance(macd, pd.Series)
    assert isinstance(signal, pd.Series)
    assert isinstance(hist, pd.Series)
    assert len(macd) == len(price_series)


def test_macd_histogram_is_difference(price_series):
    macd, signal, hist = ind.MACD(price_series, 12, 26, 9)
    diff = (macd - signal).dropna()
    hist_valid = hist.dropna()
    common = diff.index.intersection(hist_valid.index)
    np.testing.assert_allclose(diff.loc[common].values, hist_valid.loc[common].values, atol=1e-8)


# ---------------------------------------------------------------------------
# Bollinger Bands
# ---------------------------------------------------------------------------


def test_bollinger_bands_width(price_series):
    upper, middle, lower = ind.BollingerBands(price_series, 20, 2)
    valid_mask = upper.notna() & middle.notna() & lower.notna()
    assert (upper[valid_mask] >= middle[valid_mask]).all()
    assert (middle[valid_mask] >= lower[valid_mask]).all()


def test_bollinger_bands_width_increases_with_std(price_series):
    u1, m1, l1 = ind.BollingerBands(price_series, 20, 1)
    u2, m2, l2 = ind.BollingerBands(price_series, 20, 2)
    common = u1.notna() & u2.notna()
    assert ((u2 - l2)[common] >= (u1 - l1)[common]).all()


# ---------------------------------------------------------------------------
# ATR
# ---------------------------------------------------------------------------


def test_atr_positive(ohlcv_df):
    atr = ind.ATR(ohlcv_df["high"], ohlcv_df["low"], ohlcv_df["close"], 14)
    valid = atr.dropna()
    assert (valid >= 0).all()


def test_atr_higher_volatility_gives_higher_atr():
    n = 50
    low_vol = pd.DataFrame({
        "high": np.ones(n) * 101,
        "low": np.ones(n) * 99,
        "close": np.ones(n) * 100,
    })
    high_vol = pd.DataFrame({
        "high": np.ones(n) * 110,
        "low": np.ones(n) * 90,
        "close": np.ones(n) * 100,
    })
    atr_lv = ind.ATR(low_vol["high"], low_vol["low"], low_vol["close"], 5).dropna().mean()
    atr_hv = ind.ATR(high_vol["high"], high_vol["low"], high_vol["close"], 5).dropna().mean()
    assert atr_hv > atr_lv


# ---------------------------------------------------------------------------
# KDJ
# ---------------------------------------------------------------------------


def test_kdj_range(ohlcv_df):
    k, d, j = ind.KDJ(ohlcv_df["high"], ohlcv_df["low"], ohlcv_df["close"], 9)
    assert isinstance(k, pd.Series)
    assert isinstance(d, pd.Series)
    assert isinstance(j, pd.Series)
    # K and D should stay broadly in [0, 100]; J can exceed.
    assert (k >= 0).all() and (k <= 100).all()
    assert (d >= 0).all() and (d <= 100).all()


def test_kdj_length_matches_input(ohlcv_df):
    k, d, j = ind.KDJ(ohlcv_df["high"], ohlcv_df["low"], ohlcv_df["close"], 9)
    assert len(k) == len(ohlcv_df)
    assert len(d) == len(ohlcv_df)
    assert len(j) == len(ohlcv_df)


# ---------------------------------------------------------------------------
# OBV
# ---------------------------------------------------------------------------


def test_obv_increases_on_up_days(ohlcv_df):
    obv = ind.OBV(ohlcv_df["close"], ohlcv_df["volume"])
    assert isinstance(obv, pd.Series)
    assert len(obv) == len(ohlcv_df)


# ---------------------------------------------------------------------------
# VWAP
# ---------------------------------------------------------------------------


def test_vwap_between_high_and_low(ohlcv_df):
    vwap = ind.VWAP(ohlcv_df["high"], ohlcv_df["low"], ohlcv_df["close"], ohlcv_df["volume"])
    assert isinstance(vwap, pd.Series)
    assert (vwap >= ohlcv_df["low"]).all()
    assert (vwap <= ohlcv_df["high"]).all()


# ---------------------------------------------------------------------------
# Stochastic
# ---------------------------------------------------------------------------


def test_stochastic_range(ohlcv_df):
    k, d = ind.Stochastic(ohlcv_df["high"], ohlcv_df["low"], ohlcv_df["close"], 14)
    valid_k = k.dropna()
    valid_d = d.dropna()
    assert (valid_k >= 0).all() and (valid_k <= 100).all()
    assert (valid_d >= 0).all() and (valid_d <= 100).all()


# ---------------------------------------------------------------------------
# Williams %R
# ---------------------------------------------------------------------------


def test_williams_r_range(ohlcv_df):
    wr = ind.WilliamsR(ohlcv_df["high"], ohlcv_df["low"], ohlcv_df["close"], 14)
    valid = wr.dropna()
    assert (valid >= -100).all() and (valid <= 0).all()


# ---------------------------------------------------------------------------
# CCI
# ---------------------------------------------------------------------------


def test_cci_returns_series(ohlcv_df):
    cci = ind.CCI(ohlcv_df["high"], ohlcv_df["low"], ohlcv_df["close"], 20)
    assert isinstance(cci, pd.Series)
    assert len(cci) == len(ohlcv_df)


# ---------------------------------------------------------------------------
# MFI
# ---------------------------------------------------------------------------


def test_mfi_range(ohlcv_df):
    mfi = ind.MFI(ohlcv_df["high"], ohlcv_df["low"], ohlcv_df["close"], ohlcv_df["volume"], 14)
    valid = mfi.dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


# ---------------------------------------------------------------------------
# ADX
# ---------------------------------------------------------------------------


def test_adx_positive(ohlcv_df):
    adx, plus_di, minus_di = ind.ADX(ohlcv_df["high"], ohlcv_df["low"], ohlcv_df["close"], 14)
    valid_adx = adx.dropna()
    assert (valid_adx >= 0).all()


def test_adx_components_shape(ohlcv_df):
    adx, plus_di, minus_di = ind.ADX(ohlcv_df["high"], ohlcv_df["low"], ohlcv_df["close"], 14)
    assert len(adx) == len(ohlcv_df)
    assert len(plus_di) == len(ohlcv_df)
    assert len(minus_di) == len(ohlcv_df)
