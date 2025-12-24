"""
Iceberg Score System - Dual-score rating for stocks

This module implements the proprietary Iceberg Score calculation,
which provides two perspectives on stock signals:
- Trade Score: Short-term momentum and entry timing
- Investment Score: Long-term trend and value assessment

See ICEBERG_INDEX.md for full methodology documentation.

Version: 1.2 (2024-12-24)
- v1.2: Fixed post-shock recovery to use historical strength (not current uptrend)
- v1.2: Tuned post-shock bonus to +60 (HOLD rating that balances opportunity vs risk)
- v1.1: Added resilience-based scoring
- v1.1: Enhanced recovery pattern detection (post-shock recovery)
- v1.1: Context-aware RSI and volatility scoring
- v1.1: "Cheap on a winner" detection
- v1.1: Distance from high metric
"""

from typing import Optional, Tuple, List
from .models import MACDBias, RSIBias, TrendBias, VolatilityBias


# ============================================================================
# TRADE SCORE WEIGHTS v1.2 (Total: ±85 base + up to 105 bonus = ±190 max)
# ============================================================================

TRADE_MACD_WEIGHT = 25          # Momentum indicator
TRADE_RSI_WEIGHT = 15           # Strength/extremes (context-aware)
TRADE_SMA10_WEIGHT = 20         # Immediate trend
TRADE_TREND10_WEIGHT = 20       # Recovery confirmation
TRADE_VOLATILITY_WEIGHT = 5     # Risk/opportunity (resilience-aware)
TRADE_RECOVERY_BONUS = 20       # Original recovery pattern (up from 15)
TRADE_POST_SHOCK_BONUS = 60     # Post-shock recovery pattern (v1.2: HOLD rating, balances opportunity vs risk)
TRADE_CHEAP_WINNER_BONUS = 15   # Cheap on a winner pattern (NEW)
TRADE_RSI_OVERSOLD_BONUS = 10   # Extra bonus for oversold + uptrend (NEW)

TRADE_MAX_BASE_POINTS = 85


# ============================================================================
# INVESTMENT SCORE WEIGHTS v1.2 (Total: ±90 base + up to 105 bonus = ±195 max)
# ============================================================================

INV_MACD_WEIGHT = 15            # Momentum alignment
INV_RSI_WEIGHT = 10             # Strength confirmation (context-aware)
INV_SMA50_WEIGHT = 20           # Recent growth baseline
INV_TREND50_WEIGHT = 20         # Medium-term trend
INV_PRICE_VS_SMA50_WEIGHT = 15  # Distance from normal
INV_VOLATILITY_WEIGHT = 10      # Risk measure (resilience-aware)
INV_RECOVERY_BONUS = 20         # Original recovery pattern (up from 15)
INV_POST_SHOCK_BONUS = 60       # Post-shock recovery pattern (v1.2: HOLD rating, balances opportunity vs risk)
INV_CHEAP_WINNER_BONUS = 15     # Cheap on a winner pattern (NEW)
INV_RSI_OVERSOLD_BONUS = 10     # Extra bonus for oversold + uptrend (NEW)

INV_MAX_BASE_POINTS = 90


# ============================================================================
# RESILIENCE THRESHOLDS
# ============================================================================

RESILIENCE_HIGH = 3      # 3+ recoveries in 6 months = highly resilient
RESILIENCE_MEDIUM = 1    # 1-2 recoveries = medium resilience
RESILIENCE_MULTIPLIER_HIGH = 1.2
RESILIENCE_MULTIPLIER_LOW = 0.8


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


def score_rsi_contextual(
    rsi_value: Optional[float],
    rsi_bias: Optional[RSIBias],
    long_term_trend: Optional[TrendBias],
    weight: int
) -> Tuple[int, int]:
    """
    Score RSI with context awareness (v1.1).

    Oversold signals are stronger when long-term trend is UP (buying opportunity),
    weaker when long-term trend is DOWN (falling knife warning).

    Args:
        rsi_value: RSI value (0-100)
        rsi_bias: RSI bias
        long_term_trend: Long-term trend (100d SMA)
        weight: Base weight

    Returns:
        Tuple of (base_score, bonus_points)
    """
    base_score = score_rsi(rsi_value, rsi_bias, weight)
    bonus = 0

    # Extra bonus for oversold + long-term uptrend (cheap on a winner!)
    if (rsi_bias == RSIBias.OVERSOLD and
        long_term_trend == TrendBias.UP):
        bonus = TRADE_RSI_OVERSOLD_BONUS  # +10 extra points

    # Reduce oversold bonus if long-term trend is DOWN (falling knife)
    elif (rsi_bias == RSIBias.OVERSOLD and
          long_term_trend == TrendBias.DOWN):
        base_score = int(base_score * 0.3)  # Only 30% of normal oversold bonus

    return base_score, bonus


def score_volatility_resilient(
    volatility_bias: Optional[VolatilityBias],
    resilience_count: int,
    weight: int,
    score_type: str = 'investment'
) -> int:
    """
    Score volatility with resilience awareness (v1.1).

    Wild volatility is less penalized for stocks that have shown resilience.

    Args:
        volatility_bias: Volatility bias
        resilience_count: Number of recovery patterns in past 6 months
        weight: Base weight
        score_type: 'trade' or 'investment'

    Returns:
        Volatility score
    """
    if score_type == 'trade':
        base_score = score_volatility_trade(volatility_bias, weight)
    else:
        base_score = score_volatility_investment(volatility_bias, weight)

    # Adjust for resilience (only affects Wild volatility penalty)
    if volatility_bias == VolatilityBias.WILD and score_type == 'investment':
        if resilience_count >= RESILIENCE_HIGH:
            # High resilience: reduce penalty from -10 to -5
            base_score = int(base_score * 0.5)
        elif resilience_count == 0:
            # No resilience: increase penalty from -10 to -15
            base_score = int(base_score * 1.5)

    return base_score


def detect_recovery_pattern(
    current_price: float,
    sma10: Optional[float],
    sma50: Optional[float],
    trend10_bias: Optional[TrendBias],
    trend50_bias: Optional[TrendBias]
) -> bool:
    """
    Detect "buy the dip" recovery pattern (v1.0).

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


def detect_post_shock_recovery(
    current_price: float,
    distance_from_high: Optional[float],
    rsi_value: Optional[float],
    macd_hist: Optional[float],
    long_term_trend: Optional[TrendBias],
    closes: Optional[List[float]] = None,
    sma100: Optional[float] = None
) -> bool:
    """
    Detect post-shock recovery pattern (v1.2 UPDATED).

    Identifies stocks recovering after sharp drops (earnings misses, etc.)
    We can't predict the shock, but we can detect the recovery.

    v1.2 changes: No longer requires current long-term trend to be UP.
    Instead, checks if stock WAS strong before the shock (historical strength).

    Pattern criteria:
    - Price dropped >10% from 20-day high (sharp drop happened)
    - Was above SMA(100) sometime in past 60 days (had historical strength)
    - Early recovery signals (not in free fall):
      - RSI > 20 (not panic selling)
      - OR Price stabilizing (not making new lows)

    Use case: META at $594 after earnings drop from $785

    Args:
        current_price: Current stock price
        distance_from_high: % below 20-day high (negative value)
        rsi_value: RSI value
        macd_hist: MACD histogram value (legacy, not used in v1.2)
        long_term_trend: 100-day trend (legacy, not used in v1.2)
        closes: Price history for lookback check
        sma100: 100-day SMA value

    Returns:
        True if post-shock recovery detected
    """
    if distance_from_high is None:
        return False

    # Must be down significantly from recent high (sharp drop)
    if distance_from_high > -10:
        return False

    # Check historical strength: Was price above SMA(100) in past 60 days?
    # This proves stock was strong BEFORE the shock
    historical_strength = False
    if closes and sma100 and len(closes) >= 60:
        # Look at past 60 days to see if price was ever above SMA(100)
        lookback = closes[-60:]
        for i in range(len(lookback)):
            # Calculate SMA(100) at each historical point
            window = closes[:-(60-i)] if i < 59 else closes
            if len(window) >= 100:
                hist_sma100 = sum(window[-100:]) / 100
                if lookback[i] > hist_sma100:
                    historical_strength = True
                    break

    if not historical_strength:
        return False

    # Early recovery signals (relaxed - just need to not be in panic)
    rsi_not_panic = rsi_value is not None and rsi_value > 20

    # Price stabilizing (not making new lows in past 5 days)
    stabilizing = False
    if closes and len(closes) >= 5:
        recent_low = min(closes[-5:])
        stabilizing = current_price >= recent_low * 0.98  # Within 2% of recent low

    return rsi_not_panic or stabilizing


def detect_cheap_on_winner(
    current_price: float,
    sma20: Optional[float],
    sma100: Optional[float],
    long_term_trend: Optional[TrendBias],
    rsi_value: Optional[float]
) -> bool:
    """
    Detect "cheap on a winner" pattern (v1.1 NEW).

    Identifies quality stocks on temporary pullbacks.
    Different from falling knife - long-term uptrend is intact.

    Pattern criteria:
    - Price < SMA(20)         → Short-term pullback
    - Price > SMA(100)        → Long-term uptrend intact
    - Trend(100) == Up        → Structural growth continues
    - RSI < 50                → Not overbought

    Use case: GOOGL dips on broad market weakness but fundamentals strong

    Args:
        current_price: Current stock price
        sma20: 20-day SMA
        sma100: 100-day SMA
        long_term_trend: 100-day trend
        rsi_value: RSI value

    Returns:
        True if cheap on winner pattern detected
    """
    if not all([sma20, sma100, long_term_trend]):
        return False

    return (
        current_price < sma20 and
        current_price > sma100 and
        long_term_trend == TrendBias.UP and
        (rsi_value is None or rsi_value < 50)
    )


# ============================================================================
# MAIN SCORING FUNCTIONS
# ============================================================================

def calculate_trade_score(
    current_price: float,
    macd_bias: Optional[MACDBias],
    macd_hist: Optional[float],
    rsi_value: Optional[float],
    rsi_bias: Optional[RSIBias],
    sma10: Optional[float],
    sma20: Optional[float],
    sma50: Optional[float],
    sma100: Optional[float],
    trend10_bias: Optional[TrendBias],
    trend50_bias: Optional[TrendBias],
    long_term_trend: Optional[TrendBias],
    volatility_bias: Optional[VolatilityBias],
    distance_from_high: Optional[float] = None,
    resilience_count: int = 0,
    closes: Optional[List[float]] = None
) -> Tuple[int, int]:
    """
    Calculate Trade Score (0-100) for short-term trading signals (v1.1).

    Emphasizes momentum and immediate entry timing with resilience awareness.

    Args:
        current_price: Current stock price
        macd_bias: MACD indicator bias
        macd_hist: MACD histogram value
        rsi_value: RSI value (0-100)
        rsi_bias: RSI indicator bias
        sma10: 10-day simple moving average
        sma20: 20-day simple moving average
        sma50: 50-day simple moving average
        sma100: 100-day simple moving average
        trend10_bias: 10-day trend bias
        trend50_bias: 50-day trend bias
        long_term_trend: 100-day trend bias
        volatility_bias: Volatility indicator bias
        distance_from_high: % below 20-day high (negative)
        resilience_count: Number of recovery patterns in past 6 months
        closes: Price history for additional calculations (optional)

    Returns:
        Tuple of (raw_score, normalized_score_0_100)
    """
    score = 0

    # MACD momentum
    score += score_macd(macd_bias, TRADE_MACD_WEIGHT)

    # RSI strength (context-aware)
    rsi_score, rsi_bonus = score_rsi_contextual(
        rsi_value, rsi_bias, long_term_trend, TRADE_RSI_WEIGHT
    )
    score += rsi_score
    score += rsi_bonus

    # SMA(10) position
    if sma10:
        score += score_sma_position(current_price, sma10, TRADE_SMA10_WEIGHT)

    # Trend(10) direction
    score += score_trend(trend10_bias, TRADE_TREND10_WEIGHT)

    # Volatility (opportunity, resilience-aware)
    score += score_volatility_resilient(
        volatility_bias, resilience_count, TRADE_VOLATILITY_WEIGHT, 'trade'
    )

    # Original recovery pattern bonus
    if detect_recovery_pattern(current_price, sma10, sma50, trend10_bias, trend50_bias):
        bonus = TRADE_RECOVERY_BONUS
        # Apply resilience multiplier
        if resilience_count >= RESILIENCE_HIGH:
            bonus = int(bonus * RESILIENCE_MULTIPLIER_HIGH)
        elif resilience_count == 0:
            bonus = int(bonus * RESILIENCE_MULTIPLIER_LOW)
        score += bonus

    # Post-shock recovery pattern (v1.2 UPDATED)
    if detect_post_shock_recovery(
        current_price, distance_from_high, rsi_value, macd_hist, long_term_trend,
        closes=closes, sma100=sma100
    ):
        bonus = TRADE_POST_SHOCK_BONUS
        # Apply resilience multiplier
        if resilience_count >= RESILIENCE_HIGH:
            bonus = int(bonus * RESILIENCE_MULTIPLIER_HIGH)
        score += bonus

    # Cheap on a winner pattern (v1.1 NEW)
    if detect_cheap_on_winner(
        current_price, sma20, sma100, long_term_trend, rsi_value
    ):
        score += TRADE_CHEAP_WINNER_BONUS

    # Normalize to 0-100 scale (v1.1 max points increased)
    normalized = normalize_score(score, max_points=150)

    return score, normalized


def calculate_investment_score(
    current_price: float,
    macd_bias: Optional[MACDBias],
    macd_hist: Optional[float],
    rsi_value: Optional[float],
    rsi_bias: Optional[RSIBias],
    sma10: Optional[float],
    sma20: Optional[float],
    sma50: Optional[float],
    sma100: Optional[float],
    trend10_bias: Optional[TrendBias],
    trend50_bias: Optional[TrendBias],
    long_term_trend: Optional[TrendBias],
    volatility_bias: Optional[VolatilityBias],
    distance_from_high: Optional[float] = None,
    resilience_count: int = 0,
    closes: Optional[List[float]] = None
) -> Tuple[int, int]:
    """
    Calculate Investment Score (0-100) for long-term holding signals (v1.1).

    Emphasizes trend strength and value opportunities with resilience awareness.

    Args:
        current_price: Current stock price
        macd_bias: MACD indicator bias
        macd_hist: MACD histogram value
        rsi_value: RSI value (0-100)
        rsi_bias: RSI indicator bias
        sma10: 10-day simple moving average
        sma20: 20-day simple moving average
        sma50: 50-day simple moving average
        sma100: 100-day simple moving average
        trend10_bias: 10-day trend bias
        trend50_bias: 50-day trend bias
        long_term_trend: 100-day trend bias
        volatility_bias: Volatility indicator bias
        distance_from_high: % below 20-day high (negative)
        resilience_count: Number of recovery patterns in past 6 months
        closes: Price history for additional calculations (optional)

    Returns:
        Tuple of (raw_score, normalized_score_0_100)
    """
    score = 0

    # MACD alignment
    score += score_macd(macd_bias, INV_MACD_WEIGHT)

    # RSI confirmation (context-aware)
    rsi_score, rsi_bonus = score_rsi_contextual(
        rsi_value, rsi_bias, long_term_trend, INV_RSI_WEIGHT
    )
    score += rsi_score
    score += rsi_bonus

    # SMA(50) position (recent growth baseline)
    if sma50:
        score += score_sma_position(current_price, sma50, INV_SMA50_WEIGHT)

    # Trend(50) direction
    score += score_trend(trend50_bias, INV_TREND50_WEIGHT)

    # Price vs SMA(50) additional weight (distance from normal)
    if sma50:
        score += score_sma_position(current_price, sma50, INV_PRICE_VS_SMA50_WEIGHT)

    # Volatility (risk, resilience-aware)
    score += score_volatility_resilient(
        volatility_bias, resilience_count, INV_VOLATILITY_WEIGHT, 'investment'
    )

    # Original recovery pattern bonus
    if detect_recovery_pattern(current_price, sma10, sma50, trend10_bias, trend50_bias):
        bonus = INV_RECOVERY_BONUS
        # Apply resilience multiplier
        if resilience_count >= RESILIENCE_HIGH:
            bonus = int(bonus * RESILIENCE_MULTIPLIER_HIGH)
        elif resilience_count == 0:
            bonus = int(bonus * RESILIENCE_MULTIPLIER_LOW)
        score += bonus

    # Post-shock recovery pattern (v1.2 UPDATED)
    if detect_post_shock_recovery(
        current_price, distance_from_high, rsi_value, macd_hist, long_term_trend,
        closes=closes, sma100=sma100
    ):
        bonus = INV_POST_SHOCK_BONUS
        # Apply resilience multiplier
        if resilience_count >= RESILIENCE_HIGH:
            bonus = int(bonus * RESILIENCE_MULTIPLIER_HIGH)
        score += bonus

    # Cheap on a winner pattern (v1.1 NEW)
    if detect_cheap_on_winner(
        current_price, sma20, sma100, long_term_trend, rsi_value
    ):
        score += INV_CHEAP_WINNER_BONUS

    # Normalize to 0-100 scale (v1.1 max points increased)
    normalized = normalize_score(score, max_points=155)

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
