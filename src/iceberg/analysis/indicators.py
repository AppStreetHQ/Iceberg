"""Technical analysis indicators ported from StockStreet Swift"""

from typing import List, Optional
import statistics

from .models import (
    MACDResult,
    MACDBias,
    RSIResult,
    RSIBias,
    TrendSummary,
    TrendBias,
    VolatilitySummary,
    VolatilityBias,
)


def compute_ema(values: List[float], period: int) -> List[float]:
    """
    Compute Exponential Moving Average

    Args:
        values: Price values (oldest to newest)
        period: EMA period

    Returns:
        List of EMA values
    """
    if len(values) < period:
        return []

    k = 2 / (period + 1)
    ema = [values[0]]  # First EMA = first value

    for i in range(1, len(values)):
        ema.append(values[i] * k + ema[i - 1] * (1 - k))

    return ema


def compute_macd(closes: List[float]) -> Optional[MACDResult]:
    """
    Compute MACD(12,26,9) indicator

    Args:
        closes: Closing prices (oldest to newest)

    Returns:
        MACDResult or None if insufficient data
    """
    if len(closes) < 26:
        return None

    # Compute fast and slow EMAs
    fast_ema = compute_ema(closes, 12)
    slow_ema = compute_ema(closes, 26)

    if not fast_ema or not slow_ema:
        return None

    # MACD line = fast - slow
    macd_line = [f - s for f, s in zip(fast_ema, slow_ema)]

    # Signal line = EMA(9) of MACD
    signal = compute_ema(macd_line, 9)

    if not signal or len(signal) == 0:
        return None

    # Histogram = MACD - Signal
    macd_val = macd_line[-1]
    signal_val = signal[-1]
    hist = macd_val - signal_val

    # Determine bias
    if abs(hist) < 0.01:
        bias = MACDBias.NEUTRAL
    elif hist > 0:
        bias = MACDBias.BULL
    else:
        bias = MACDBias.BEAR

    return MACDResult(macd=macd_val, signal=signal_val, hist=hist, bias=bias)


def compute_rsi(closes: List[float], period: int = 14) -> Optional[RSIResult]:
    """
    Compute RSI indicator

    Args:
        closes: Closing prices (oldest to newest)
        period: RSI period (default 14)

    Returns:
        RSIResult or None if insufficient data
    """
    if len(closes) < period + 1:
        return None

    # Calculate gains and losses
    gains = []
    losses = []

    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(0, change))
        losses.append(max(0, -change))

    # Average gains and losses over period
    if len(gains) < period:
        return None

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    # Calculate RSI
    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    # Determine bias
    if rsi >= 70:
        bias = RSIBias.OVERBOUGHT
    elif rsi >= 55:
        bias = RSIBias.STRONG
    elif rsi >= 45:
        bias = RSIBias.NEUTRAL
    elif rsi >= 30:
        bias = RSIBias.WEAK
    else:
        bias = RSIBias.OVERSOLD

    return RSIResult(value=rsi, bias=bias)


def compute_sma(closes: List[float], period: int = 20) -> Optional[float]:
    """
    Compute Simple Moving Average

    Args:
        closes: Closing prices (oldest to newest)
        period: SMA period (default 20)

    Returns:
        SMA value or None if insufficient data
    """
    if len(closes) < period:
        return None

    return sum(closes[-period:]) / period


def compute_trend(closes: List[float], sma_period: int = 20) -> Optional[TrendSummary]:
    """
    Compute trend analysis using SMA

    Args:
        closes: Closing prices (oldest to newest)
        sma_period: SMA period for trend calculation

    Returns:
        TrendSummary or None if insufficient data
    """
    sma = compute_sma(closes, sma_period)
    if sma is None or len(closes) == 0:
        return None

    last_price = closes[-1]
    delta_pct = ((last_price - sma) / sma) * 100

    # Determine trend bias
    if delta_pct > 2.0:
        bias = TrendBias.UP
    elif delta_pct < -2.0:
        bias = TrendBias.DOWN
    else:
        bias = TrendBias.SIDEWAYS

    return TrendSummary(sma_value=sma, delta_pct=delta_pct, bias=bias)


def compute_volatility(closes: List[float]) -> Optional[VolatilitySummary]:
    """
    Compute volatility using standard deviation of daily returns

    Args:
        closes: Closing prices (oldest to newest)

    Returns:
        VolatilitySummary or None if insufficient data
    """
    if len(closes) < 2:
        return None

    # Calculate daily returns
    returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] != 0:
            ret = ((closes[i] - closes[i - 1]) / closes[i - 1]) * 100
            returns.append(ret)

    if len(returns) < 2:
        return None

    # Calculate standard deviation
    sigma = statistics.stdev(returns)

    # Determine volatility bias
    if sigma < 1.0:
        bias = VolatilityBias.CALM
    elif sigma < 3.0:
        bias = VolatilityBias.CHOPPY
    else:
        bias = VolatilityBias.WILD

    return VolatilitySummary(sigma=sigma, bias=bias)
