"""
Iceberg Score System - Dual-score rating for stocks

This module implements the proprietary Iceberg Score calculation,
which provides two perspectives on stock signals:
- Trade Score: Short-term momentum and entry timing
- Investment Score: Long-term trend and value assessment

See ICEBERG_INDEX.md for full methodology documentation.

Version: 1.0 (2024-12-24)
"""

from typing import Optional, Tuple
from .models import MACDBias, RSIBias, TrendBias, VolatilityBias


# ============================================================================
# TRADE SCORE WEIGHTS (Total: ±85 base + 15 bonus = ±100 max)
# ============================================================================

TRADE_MACD_WEIGHT = 25          # Momentum indicator
TRADE_RSI_WEIGHT = 15           # Strength/extremes
TRADE_SMA10_WEIGHT = 20         # Immediate trend
TRADE_TREND10_WEIGHT = 20       # Recovery confirmation
TRADE_VOLATILITY_WEIGHT = 5     # Risk/opportunity
TRADE_RECOVERY_BONUS = 15       # Pattern detection bonus

TRADE_MAX_BASE_POINTS = 85


# ============================================================================
# INVESTMENT SCORE WEIGHTS (Total: ±80 base + 15 bonus = ±95 max)
# ============================================================================

INV_MACD_WEIGHT = 15            # Momentum alignment
INV_RSI_WEIGHT = 10             # Strength confirmation
INV_SMA50_WEIGHT = 20           # Recent growth baseline
INV_TREND50_WEIGHT = 20         # Medium-term trend
INV_PRICE_VS_SMA50_WEIGHT = 15  # Distance from normal
INV_VOLATILITY_WEIGHT = 10      # Risk measure
INV_RECOVERY_BONUS = 15         # Pattern detection bonus

INV_MAX_BASE_POINTS = 90


# ============================================================================
# COMPONENT SCORING FUNCTIONS
# ============================================================================

def score_macd(macd_bias: Optional[MACDBias], weight: int) -> int:
    """
    Score MACD momentum indicator.

    Args:
        macd_bias: Bull/Bear/Neutral
        weight: Points to assign for bull signal

    Returns:
        +weight for Bull, -weight for Bear, 0 for Neutral/None
    """
    if not macd_bias:
        return 0

    if macd_bias == MACDBias.BULL:
        return weight
    elif macd_bias == MACDBias.BEAR:
        return -weight
    else:
        return 0


def score_rsi(rsi_value: Optional[float], rsi_bias: Optional[RSIBias], weight: int) -> int:
    """
    Score RSI strength indicator.

    RSI ranges and scores (based on weight=15):
    - Oversold (<30): +15 (buying opportunity)
    - Weak (30-40): -10
    - Neutral (40-60): 0
    - Strong (60-70): +10
    - Overbought (>70): -15 (sell signal)

    Args:
        rsi_value: RSI value (0-100)
        rsi_bias: Overbought/Strong/Neutral/Weak/Oversold
        weight: Base weight for overbought/oversold

    Returns:
        Weighted score based on RSI level
    """
    if not rsi_bias or rsi_value is None:
        return 0

    if rsi_bias == RSIBias.OVERSOLD:
        return weight  # Buying opportunity
    elif rsi_bias == RSIBias.WEAK:
        return int(-weight * 0.67)  # -10 when weight=15
    elif rsi_bias == RSIBias.NEUTRAL:
        return 0
    elif rsi_bias == RSIBias.STRONG:
        return int(weight * 0.67)  # +10 when weight=15
    elif rsi_bias == RSIBias.OVERBOUGHT:
        return -weight  # Sell signal
    else:
        return 0


def score_sma_position(
    current_price: float,
    sma_value: float,
    weight: int
) -> int:
    """
    Score price position relative to SMA.

    Formula: ((Price - SMA) / SMA) × 100, capped at ±weight

    Args:
        current_price: Current stock price
        sma_value: Simple moving average value
        weight: Maximum points (cap)

    Returns:
        Score capped at ±weight
    """
    if not sma_value or sma_value == 0:
        return 0

    pct_diff = ((current_price - sma_value) / sma_value) * 100
    score = int(pct_diff)

    # Cap at weight limit
    return max(-weight, min(weight, score))


def score_trend(trend_bias: Optional[TrendBias], weight: int) -> int:
    """
    Score trend direction.

    Args:
        trend_bias: Up/Down/Sideways
        weight: Points for up trend

    Returns:
        +weight for Up, -weight for Down, 0 for Sideways/None
    """
    if not trend_bias:
        return 0

    if trend_bias == TrendBias.UP:
        return weight
    elif trend_bias == TrendBias.DOWN:
        return -weight
    else:
        return 0


def score_volatility_trade(volatility_bias: Optional[VolatilityBias], weight: int) -> int:
    """
    Score volatility for Trade Score (volatility = opportunity).

    Args:
        volatility_bias: Calm/Choppy/Wild
        weight: Points for calm/wild (both positive)

    Returns:
        +weight for Calm or Wild, 0 for Choppy/None
    """
    if not volatility_bias:
        return 0

    if volatility_bias in (VolatilityBias.CALM, VolatilityBias.WILD):
        return weight
    else:
        return 0


def score_volatility_investment(volatility_bias: Optional[VolatilityBias], weight: int) -> int:
    """
    Score volatility for Investment Score (volatility = risk).

    Args:
        volatility_bias: Calm/Choppy/Wild
        weight: Points for calm (positive) or wild (negative)

    Returns:
        +weight for Calm, -weight for Wild, 0 for Choppy/None
    """
    if not volatility_bias:
        return 0

    if volatility_bias == VolatilityBias.CALM:
        return weight
    elif volatility_bias == VolatilityBias.WILD:
        return -weight
    else:
        return 0


def detect_recovery_pattern(
    current_price: float,
    sma10: Optional[float],
    sma50: Optional[float],
    trend10_bias: Optional[TrendBias],
    trend50_bias: Optional[TrendBias]
) -> bool:
    """
    Detect "buy the dip" recovery pattern.

    Pattern criteria:
    - Price < SMA(50)     → Below recent high (pullback happened)
    - Price > SMA(10)     → Above immediate low (recovery starting)
    - Trend(10) == Up     → Momentum turning positive
    - Trend(50) == Up     → Long-term growth still intact

    Use case: High-growth stocks (RKLB, NVDA) bouncing from temporary
    pullbacks. Catches multiple re-entry opportunities.

    Args:
        current_price: Current stock price
        sma10: 10-day SMA
        sma50: 50-day SMA
        trend10_bias: Short-term trend
        trend50_bias: Medium-term trend

    Returns:
        True if recovery pattern detected
    """
    if not all([sma10, sma50, trend10_bias, trend50_bias]):
        return False

    return (
        current_price < sma50 and
        current_price > sma10 and
        trend10_bias == TrendBias.UP and
        trend50_bias == TrendBias.UP
    )


# ============================================================================
# MAIN SCORING FUNCTIONS
# ============================================================================

def calculate_trade_score(
    current_price: float,
    macd_bias: Optional[MACDBias],
    rsi_value: Optional[float],
    rsi_bias: Optional[RSIBias],
    sma10: Optional[float],
    trend10_bias: Optional[TrendBias],
    sma50: Optional[float],
    trend50_bias: Optional[TrendBias],
    volatility_bias: Optional[VolatilityBias]
) -> Tuple[int, int]:
    """
    Calculate Trade Score (0-100) for short-term trading signals.

    Emphasizes momentum and immediate entry timing.

    Args:
        current_price: Current stock price
        macd_bias: MACD indicator bias
        rsi_value: RSI value (0-100)
        rsi_bias: RSI indicator bias
        sma10: 10-day simple moving average
        trend10_bias: 10-day trend bias
        sma50: 50-day simple moving average (for recovery pattern)
        trend50_bias: 50-day trend bias (for recovery pattern)
        volatility_bias: Volatility indicator bias

    Returns:
        Tuple of (raw_score, normalized_score_0_100)
    """
    score = 0

    # MACD momentum
    score += score_macd(macd_bias, TRADE_MACD_WEIGHT)

    # RSI strength
    score += score_rsi(rsi_value, rsi_bias, TRADE_RSI_WEIGHT)

    # SMA(10) position
    if sma10:
        score += score_sma_position(current_price, sma10, TRADE_SMA10_WEIGHT)

    # Trend(10) direction
    score += score_trend(trend10_bias, TRADE_TREND10_WEIGHT)

    # Volatility (opportunity)
    score += score_volatility_trade(volatility_bias, TRADE_VOLATILITY_WEIGHT)

    # Recovery pattern bonus
    if detect_recovery_pattern(current_price, sma10, sma50, trend10_bias, trend50_bias):
        score += TRADE_RECOVERY_BONUS

    # Normalize to 0-100 scale
    normalized = normalize_score(score, max_points=100)

    return score, normalized


def calculate_investment_score(
    current_price: float,
    macd_bias: Optional[MACDBias],
    rsi_value: Optional[float],
    rsi_bias: Optional[RSIBias],
    sma10: Optional[float],
    sma50: Optional[float],
    trend10_bias: Optional[TrendBias],
    trend50_bias: Optional[TrendBias],
    volatility_bias: Optional[VolatilityBias]
) -> Tuple[int, int]:
    """
    Calculate Investment Score (0-100) for long-term holding signals.

    Emphasizes trend strength and value opportunities.

    Args:
        current_price: Current stock price
        macd_bias: MACD indicator bias
        rsi_value: RSI value (0-100)
        rsi_bias: RSI indicator bias
        sma10: 10-day simple moving average (for recovery pattern)
        sma50: 50-day simple moving average
        trend10_bias: 10-day trend bias (for recovery pattern)
        trend50_bias: 50-day trend bias
        volatility_bias: Volatility indicator bias

    Returns:
        Tuple of (raw_score, normalized_score_0_100)
    """
    score = 0

    # MACD alignment
    score += score_macd(macd_bias, INV_MACD_WEIGHT)

    # RSI confirmation
    score += score_rsi(rsi_value, rsi_bias, INV_RSI_WEIGHT)

    # SMA(50) position (recent growth baseline)
    if sma50:
        score += score_sma_position(current_price, sma50, INV_SMA50_WEIGHT)

    # Trend(50) direction
    score += score_trend(trend50_bias, INV_TREND50_WEIGHT)

    # Price vs SMA(50) additional weight (distance from normal)
    if sma50:
        score += score_sma_position(current_price, sma50, INV_PRICE_VS_SMA50_WEIGHT)

    # Volatility (risk)
    score += score_volatility_investment(volatility_bias, INV_VOLATILITY_WEIGHT)

    # Recovery pattern bonus
    if detect_recovery_pattern(current_price, sma10, sma50, trend10_bias, trend50_bias):
        score += INV_RECOVERY_BONUS

    # Normalize to 0-100 scale
    normalized = normalize_score(score, max_points=95)

    return score, normalized


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def normalize_score(raw_score: int, max_points: int) -> int:
    """
    Normalize raw score to 0-100 scale.

    Formula: ((RawScore + MaxPoints) / (MaxPoints × 2)) × 100

    Args:
        raw_score: Raw score from weighted calculations
        max_points: Maximum possible points (positive or negative)

    Returns:
        Score on 0-100 scale
    """
    normalized = ((raw_score + max_points) / (max_points * 2)) * 100
    return int(round(normalized))


def get_rating_label(score: int) -> str:
    """
    Convert numeric score to categorical rating.

    Score ranges:
    - 85-100: STRONG BUY
    - 70-84: BUY
    - 55-69: OUTPERFORM
    - 45-54: HOLD
    - 30-44: UNDERPERFORM
    - 0-29: SELL

    Args:
        score: Normalized score (0-100)

    Returns:
        Rating label string
    """
    if score >= 85:
        return "STRONG BUY"
    elif score >= 70:
        return "BUY"
    elif score >= 55:
        return "OUTPERFORM"
    elif score >= 45:
        return "HOLD"
    elif score >= 30:
        return "UNDERPERFORM"
    else:
        return "SELL"


def get_rating_color(score: int) -> str:
    """
    Get color for score/rating display.

    Args:
        score: Normalized score (0-100)

    Returns:
        Hex color code
    """
    if score >= 70:
        return "#00ff00"  # Green - Buy signals
    elif score >= 55:
        return "#88ff88"  # Light green - Outperform
    elif score >= 45:
        return "#888888"  # Gray - Hold
    elif score >= 30:
        return "#ff8888"  # Light red - Underperform
    else:
        return "#ff0000"  # Red - Sell signals


def generate_score_bar(score: int, width: int = 20) -> str:
    """
    Generate ASCII bar visualization for score.

    Args:
        score: Normalized score (0-100)
        width: Total width of bar in characters

    Returns:
        ASCII bar string (e.g., "████████████░░░░░░░░")
    """
    filled_chars = int((score / 100) * width)
    empty_chars = width - filled_chars
    return "█" * filled_chars + "░" * empty_chars
