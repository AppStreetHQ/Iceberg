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


def compute_distance_from_high(closes: List[float], period: int = 20) -> Optional[float]:
    """
    Calculate percentage distance from recent high

    Used to detect pullbacks and identify "cheap on a winner" opportunities.

    Args:
        closes: Closing prices (oldest to newest)
        period: Period to look back for high (default 20 days)

    Returns:
        Percentage below recent high (negative value) or None if insufficient data
        Example: -15.5 means current price is 15.5% below the 20-day high
    """
    if len(closes) < period + 1:
        return None

    recent_closes = closes[-period:]
    recent_high = max(recent_closes)
    current_price = closes[-1]

    if recent_high == 0:
        return None

    distance_pct = ((current_price - recent_high) / recent_high) * 100
    return distance_pct


def count_recovery_patterns(closes: List[float], lookback_days: int = 180) -> int:
    """
    Count recovery patterns over a lookback period to measure resilience.

    Recovery pattern: Price drops below SMA(50), then recovers back above it
    with upward momentum. This indicates a stock that bounces back from dips.

    Args:
        closes: Closing prices (oldest to newest)
        lookback_days: Days to look back (default 180 = ~6 months)

    Returns:
        Number of recovery patterns detected (resilience score)
    """
    if len(closes) < 50:
        return 0

    # Use only lookback period
    start_idx = max(0, len(closes) - lookback_days)
    period_closes = closes[start_idx:]

    if len(period_closes) < 50:
        return 0

    recovery_count = 0
    in_dip = False

    # Scan through the period looking for dip → recovery patterns
    for i in range(50, len(period_closes)):
        window = period_closes[:i+1]
        sma50 = compute_sma(window, 50)
        sma10 = compute_sma(window, 10)
        current_price = window[-1]

        if sma50 is None or sma10 is None:
            continue

        # Detect dip: price below SMA(50)
        if current_price < sma50 and not in_dip:
            in_dip = True

        # Detect recovery: price back above SMA(50) with momentum
        elif current_price > sma50 and in_dip:
            # Confirm recovery with upward momentum
            if current_price > sma10:
                recovery_count += 1
            in_dip = False

    return recovery_count


def compute_long_term_trend(closes: List[float], period: int = 100) -> Optional[TrendBias]:
    """
    Determine long-term trend using longer SMA period.

    Used to distinguish "cheap on a winner" from "falling knife".

    Args:
        closes: Closing prices (oldest to newest)
        period: SMA period for long-term trend (default 100)

    Returns:
        TrendBias (UP/DOWN/SIDEWAYS) or None if insufficient data
    """
    trend = compute_trend(closes, period)
    return trend.bias if trend else None
