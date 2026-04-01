"""
Technical indicators implemented with pure numpy / pandas – no TA-Lib dependency.

All functions accept array-like inputs (pandas Series or numpy arrays) and
return pandas Series (or tuples of Series) with the same index preserved when
a Series is supplied.
"""

from __future__ import annotations

from typing import Tuple, Union

import numpy as np
import pandas as pd

_Array = Union[pd.Series, np.ndarray]


def _to_series(data: _Array, name: str = "") -> pd.Series:
    """Coerce ndarray/list to pd.Series; preserve Series as-is."""
    if isinstance(data, pd.Series):
        return data
    return pd.Series(data, name=name)


# ---------------------------------------------------------------------------
# Trend
# ---------------------------------------------------------------------------


def SMA(data: _Array, period: int) -> pd.Series:
    """Simple Moving Average.

    Parameters
    ----------
    data : array-like
        Price series (typically close prices).
    period : int
        Look-back window.

    Returns
    -------
    pd.Series
    """
    s = _to_series(data, "close")
    return s.rolling(window=period, min_periods=period).mean().rename(f"SMA_{period}")


def EMA(data: _Array, period: int) -> pd.Series:
    """Exponential Moving Average.

    Parameters
    ----------
    data : array-like
        Price series.
    period : int
        Span (number of periods).

    Returns
    -------
    pd.Series
    """
    s = _to_series(data, "close")
    return s.ewm(span=period, adjust=False, min_periods=period).mean().rename(f"EMA_{period}")


def MACD(
    data: _Array,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Moving Average Convergence Divergence.

    Parameters
    ----------
    data : array-like
        Price series.
    fast : int
        Fast EMA period.
    slow : int
        Slow EMA period.
    signal : int
        Signal line EMA period.

    Returns
    -------
    (macd, signal_line, histogram) : tuple of pd.Series
    """
    s = _to_series(data, "close")
    ema_fast = s.ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = s.ewm(span=slow, adjust=False, min_periods=slow).mean()
    macd_line = (ema_fast - ema_slow).rename("MACD")
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean().rename("MACD_Signal")
    histogram = (macd_line - signal_line).rename("MACD_Hist")
    return macd_line, signal_line, histogram


# ---------------------------------------------------------------------------
# Momentum
# ---------------------------------------------------------------------------


def RSI(data: _Array, period: int = 14) -> pd.Series:
    """Relative Strength Index.

    Computed using Wilder's smoothing (equivalent to EMA with
    ``alpha = 1/period``).

    Parameters
    ----------
    data : array-like
        Price series.
    period : int
        Look-back period.

    Returns
    -------
    pd.Series
        Values in the range [0, 100].
    """
    s = _to_series(data, "close")
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.rename(f"RSI_{period}")


def Stochastic(
    high: _Array,
    low: _Array,
    close: _Array,
    period: int = 14,
    smooth_k: int = 3,
    smooth_d: int = 3,
) -> Tuple[pd.Series, pd.Series]:
    """Stochastic Oscillator (%K and %D).

    Parameters
    ----------
    high, low, close : array-like
    period : int
        %K raw look-back window.
    smooth_k : int
        SMA smoothing applied to raw %K.
    smooth_d : int
        SMA smoothing applied to smoothed %K to derive %D.

    Returns
    -------
    (k, d) : tuple of pd.Series
    """
    h = _to_series(high)
    l = _to_series(low)
    c = _to_series(close)
    lowest = l.rolling(period).min()
    highest = h.rolling(period).max()
    raw_k = 100.0 * (c - lowest) / (highest - lowest).replace(0, np.nan)
    k = raw_k.rolling(smooth_k).mean().rename(f"STOCH_K_{period}")
    d = k.rolling(smooth_d).mean().rename(f"STOCH_D_{period}")
    return k, d


def WilliamsR(
    high: _Array,
    low: _Array,
    close: _Array,
    period: int = 14,
) -> pd.Series:
    """Williams %R.

    Returns values in the range [-100, 0].
    """
    h = _to_series(high)
    l = _to_series(low)
    c = _to_series(close)
    highest = h.rolling(period).max()
    lowest = l.rolling(period).min()
    wr = -100.0 * (highest - c) / (highest - lowest).replace(0, np.nan)
    return wr.rename(f"WR_{period}")


def CCI(
    high: _Array,
    low: _Array,
    close: _Array,
    period: int = 20,
) -> pd.Series:
    """Commodity Channel Index.

    Parameters
    ----------
    high, low, close : array-like
    period : int

    Returns
    -------
    pd.Series
    """
    h = _to_series(high)
    l = _to_series(low)
    c = _to_series(close)
    tp = (h + l + c) / 3.0
    sma_tp = tp.rolling(period).mean()
    mean_dev = tp.rolling(period).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    cci = (tp - sma_tp) / (0.015 * mean_dev.replace(0, np.nan))
    return cci.rename(f"CCI_{period}")


def MFI(
    high: _Array,
    low: _Array,
    close: _Array,
    volume: _Array,
    period: int = 14,
) -> pd.Series:
    """Money Flow Index.

    Parameters
    ----------
    high, low, close, volume : array-like
    period : int

    Returns
    -------
    pd.Series
        Values in [0, 100].
    """
    h = _to_series(high)
    l = _to_series(low)
    c = _to_series(close)
    v = _to_series(volume)
    tp = (h + l + c) / 3.0
    raw_mf = tp * v
    delta_tp = tp.diff()
    pos_mf = raw_mf.where(delta_tp > 0, 0.0)
    neg_mf = raw_mf.where(delta_tp < 0, 0.0)
    pos_sum = pos_mf.rolling(period).sum()
    neg_sum = neg_mf.rolling(period).sum().abs()
    mfr = pos_sum / neg_sum.replace(0, np.nan)
    mfi = 100.0 - (100.0 / (1.0 + mfr))
    return mfi.rename(f"MFI_{period}")


def KDJ(
    high: _Array,
    low: _Array,
    close: _Array,
    period: int = 9,
    signal: int = 3,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """KDJ Indicator (popular in Asian markets).

    Parameters
    ----------
    high, low, close : array-like
    period : int
        RSV look-back window.
    signal : int
        Smoothing factor denominator.

    Returns
    -------
    (k, d, j) : tuple of pd.Series
    """
    h = _to_series(high)
    l = _to_series(low)
    c = _to_series(close)
    lowest = l.rolling(period).min()
    highest = h.rolling(period).max()
    rsv = 100.0 * (c - lowest) / (highest - lowest).replace(0, np.nan)
    rsv = rsv.fillna(50.0)

    k_vals = np.full(len(rsv), 50.0)
    d_vals = np.full(len(rsv), 50.0)
    for i in range(1, len(rsv)):
        k_vals[i] = (signal - 1) / signal * k_vals[i - 1] + rsv.iloc[i] / signal
        d_vals[i] = (signal - 1) / signal * d_vals[i - 1] + k_vals[i] / signal

    idx = rsv.index
    k = pd.Series(k_vals, index=idx, name=f"KDJ_K_{period}")
    d = pd.Series(d_vals, index=idx, name=f"KDJ_D_{period}")
    j = (3 * k - 2 * d).rename(f"KDJ_J_{period}")
    return k, d, j


# ---------------------------------------------------------------------------
# Volatility
# ---------------------------------------------------------------------------


def BollingerBands(
    data: _Array,
    period: int = 20,
    std: float = 2.0,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands.

    Parameters
    ----------
    data : array-like
        Price series.
    period : int
        Rolling mean window.
    std : float
        Number of standard deviations for upper/lower bands.

    Returns
    -------
    (upper, middle, lower) : tuple of pd.Series
    """
    s = _to_series(data, "close")
    middle = s.rolling(period).mean().rename("BB_Mid")
    sigma = s.rolling(period).std(ddof=0)
    upper = (middle + std * sigma).rename("BB_Upper")
    lower = (middle - std * sigma).rename("BB_Lower")
    return upper, middle, lower


def ATR(
    high: _Array,
    low: _Array,
    close: _Array,
    period: int = 14,
) -> pd.Series:
    """Average True Range.

    Parameters
    ----------
    high, low, close : array-like
    period : int

    Returns
    -------
    pd.Series
        Non-negative ATR values.
    """
    h = _to_series(high)
    l = _to_series(low)
    c = _to_series(close)
    prev_close = c.shift(1)
    tr = pd.concat(
        [
            (h - l).rename("hl"),
            (h - prev_close).abs().rename("hpc"),
            (l - prev_close).abs().rename("lpc"),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    return atr.rename(f"ATR_{period}")


def ADX(
    high: _Array,
    low: _Array,
    close: _Array,
    period: int = 14,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Average Directional Index.

    Parameters
    ----------
    high, low, close : array-like
    period : int

    Returns
    -------
    (adx, plus_di, minus_di) : tuple of pd.Series
    """
    h = _to_series(high)
    l = _to_series(low)
    c = _to_series(close)

    prev_h = h.shift(1)
    prev_l = l.shift(1)
    prev_c = c.shift(1)

    tr = pd.concat(
        [
            (h - l).rename("hl"),
            (h - prev_c).abs().rename("hpc"),
            (l - prev_c).abs().rename("lpc"),
        ],
        axis=1,
    ).max(axis=1)

    up_move = h - prev_h
    down_move = prev_l - l

    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    atr_s = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    plus_dm_s = plus_dm.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    minus_dm_s = minus_dm.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()

    plus_di = (100.0 * plus_dm_s / atr_s.replace(0, np.nan)).rename(f"+DI_{period}")
    minus_di = (100.0 * minus_dm_s / atr_s.replace(0, np.nan)).rename(f"-DI_{period}")

    dx = (100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx = dx.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean().rename(f"ADX_{period}")
    return adx, plus_di, minus_di


# ---------------------------------------------------------------------------
# Volume
# ---------------------------------------------------------------------------


def OBV(close: _Array, volume: _Array) -> pd.Series:
    """On-Balance Volume.

    Parameters
    ----------
    close : array-like
    volume : array-like

    Returns
    -------
    pd.Series
    """
    c = _to_series(close)
    v = _to_series(volume)
    direction = np.sign(c.diff().fillna(0))
    obv = (direction * v).cumsum()
    return obv.rename("OBV")


def VWAP(
    high: _Array,
    low: _Array,
    close: _Array,
    volume: _Array,
) -> pd.Series:
    """Volume-Weighted Average Price.

    Computed as the cumulative (typical price × volume) / cumulative volume.
    Resets are not applied (use intraday DataFrames for session-level VWAP).

    Parameters
    ----------
    high, low, close, volume : array-like

    Returns
    -------
    pd.Series
    """
    h = _to_series(high)
    l = _to_series(low)
    c = _to_series(close)
    v = _to_series(volume)
    tp = (h + l + c) / 3.0
    cum_tp_vol = (tp * v).cumsum()
    cum_vol = v.cumsum()
    vwap = cum_tp_vol / cum_vol.replace(0, np.nan)
    return vwap.rename("VWAP")
