"""
Iceberg Score System - Dual-score rating for stocks

This module implements the proprietary Iceberg Score calculation,
which provides two perspectives on stock signals:
- Trade Score: Short-term momentum and entry timing
- Investment Score: Long-term trend and value assessment

See ICEBERG_INDEX.md for full methodology documentation.

Version: 1.3 (2024-12-24)
- v1.3: "Proven Winner Capitulation" pattern for extreme high-confidence setups
- v1.3: Trade +120, Investment +100 bonuses for clear-cut capitulation opportunities
- v1.3: Very specific criteria: rally >40%, drop >30%, RSI <20, back at support
- v1.2: Fixed post-shock recovery to use historical strength (not current uptrend)
- v1.2: Tuned post-shock bonus to +60 (HOLD rating that balances opportunity vs risk)
- v1.1: Added resilience-based scoring
- v1.1: Enhanced recovery pattern detection (post-shock recovery)
- v1.1: Context-aware RSI and volatility scoring
- v1.1: "Cheap on a winner" detection
- v1.1: Distance from high metric
"""

from typing import Optional, Tuple, List
from dataclasses import dataclass
from .models import MACDBias, RSIBias, TrendBias, VolatilityBias


@dataclass
class ScoreResult:
    """Result containing both turnaround and BAU scores."""
    turnaround_raw: int
    turnaround_score: int
    bau_raw: int
    bau_score: int
    turnaround_active: bool

    @property
    def display_score(self) -> int:
        """Primary score to display (turnaround if active, else BAU)."""
        return self.turnaround_score if self.turnaround_active else self.bau_score

    @property
    def display_raw(self) -> int:
        """Primary raw score to display."""
        return self.turnaround_raw if self.turnaround_active else self.bau_raw


# ============================================================================
# TRADE SCORE WEIGHTS v1.3 (Total: ±85 base + up to 310 bonus = ±395 max)
# ============================================================================

TRADE_MACD_WEIGHT = 25          # Momentum indicator
TRADE_RSI_WEIGHT = 15           # Strength/extremes (context-aware)
TRADE_SMA10_WEIGHT = 20         # Immediate trend
TRADE_TREND10_WEIGHT = 20       # Recovery confirmation
TRADE_VOLATILITY_WEIGHT = 5     # Risk/opportunity (resilience-aware)
TRADE_RECOVERY_BONUS = 20        # Original recovery pattern (up from 15)
TRADE_POST_SHOCK_BONUS = 60      # Post-shock recovery pattern (v1.2: broad cases)
TRADE_CAPITULATION_BONUS = 205   # Proven winner capitulation (v1.3: AGGRESSIVE for traders)
TRADE_CHEAP_WINNER_BONUS = 15    # Cheap on a winner pattern (v1.1)
TRADE_RSI_OVERSOLD_BONUS = 10    # Extra bonus for oversold + uptrend (v1.1)

TRADE_MAX_BASE_POINTS = 85


# ============================================================================
# INVESTMENT SCORE WEIGHTS v1.3 (Total: ±90 base + up to 165 bonus = ±255 max)
# ============================================================================

INV_MACD_WEIGHT = 15            # Momentum alignment
INV_RSI_WEIGHT = 10             # Strength confirmation (context-aware)
INV_SMA50_WEIGHT = 20           # Recent growth baseline
INV_TREND50_WEIGHT = 20         # Medium-term trend
INV_PRICE_VS_SMA50_WEIGHT = 15  # Distance from normal
INV_VOLATILITY_WEIGHT = 10      # Risk measure (resilience-aware)
INV_RECOVERY_BONUS = 20          # Original recovery pattern (up from 15)
INV_POST_SHOCK_BONUS = 60        # Post-shock recovery pattern (v1.2: broad cases)
INV_CAPITULATION_BONUS = 60      # Proven winner capitulation (v1.3: CAUTIOUS for investors)
INV_CHEAP_WINNER_BONUS = 15      # Cheap on a winner pattern (v1.1)
INV_RSI_OVERSOLD_BONUS = 10      # Extra bonus for oversold + uptrend (v1.1)

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


def detect_proven_winner_capitulation(
    current_price: float,
    closes: Optional[List[float]],
    sma100: Optional[float],
    rsi_value: Optional[float],
    distance_from_high: Optional[float]
) -> bool:
    """
    Detect "proven winner capitulation" pattern (v1.3 NEW).

    Extremely specific, high-confidence pattern for stocks with recent
    proven strength that have capitulated to extreme oversold levels.

    Pattern criteria (ALL must be true):
    1. Stock rallied >40% in past 90 days (proven it can run)
    2. Then dropped >30% from that high (sharp correction)
    3. RSI < 20 (extreme panic, not just oversold)
    4. Price near or below where rally started (back at support)
    5. Was above SMA(100) during rally (confirmed strength)

    This is VERY specific - designed to catch clear-cut capitulation
    opportunities like RKLB Nov 21 at $40 (after Jul-Sep rally).

    Args:
        current_price: Current stock price
        closes: List of closing prices (need 90+ days)
        sma100: 100-day SMA
        rsi_value: RSI value
        distance_from_high: % distance from recent high

    Returns:
        True if proven winner capitulation detected
    """
    # Need sufficient data
    if not closes or len(closes) < 90:
        return False

    # Criterion 3: RSI < 20 (extreme panic)
    if rsi_value is None or rsi_value >= 20:
        return False

    # Criterion 2: Dropped >30% from high
    if distance_from_high is None or distance_from_high > -30:
        return False

    # Find the peak in past 90 days (the top before the crash)
    lookback_90d = closes[-90:]
    rally_peak_price = max(lookback_90d)
    peak_idx = len(closes) - 90 + lookback_90d.index(rally_peak_price)

    # Find the rally start: lowest point BEFORE the peak (in first half of lookback)
    # This avoids finding the current price as the "start"
    prices_before_peak = closes[max(0, len(closes)-90):peak_idx+1]
    if len(prices_before_peak) < 30:  # Need reasonable data before peak
        return False

    rally_start_price = min(prices_before_peak)
    rally_start_idx = max(0, len(closes)-90) + prices_before_peak.index(rally_start_price)

    # Criterion 1: Rally >40% from start to peak
    rally_gain_pct = ((rally_peak_price - rally_start_price) / rally_start_price) * 100
    if rally_gain_pct < 40:
        return False

    # Criterion 4: Price near or below rally start (back at support)
    # Allow some tolerance - within 10% above rally start
    if current_price > rally_start_price * 1.10:
        return False

    # Criterion 5: Was above SMA(100) during the rally
    # Check if price was above SMA100 at any point during rally
    if sma100 is None:
        return False

    was_above_sma100 = False
    for i in range(rally_start_idx, len(closes)):
        # Calculate SMA100 at this point in time
        if i >= 100:
            historical_sma100 = sum(closes[i-100:i]) / 100
            if closes[i] > historical_sma100:
                was_above_sma100 = True
                break

    if not was_above_sma100:
        return False

    # All criteria met - this is a proven winner capitulation!
    return True


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

    # Check pattern detections
    capitulation_detected = detect_proven_winner_capitulation(
        current_price, closes, sma100, rsi_value, distance_from_high
    )
    post_shock_detected = detect_post_shock_recovery(
        current_price, distance_from_high, rsi_value, macd_hist, long_term_trend,
        closes=closes, sma100=sma100
    )
    cheap_winner_detected = detect_cheap_on_winner(
        current_price, sma20, sma100, long_term_trend, rsi_value
    )

    # Calculate TURNAROUND score (uses capitulation bonus if detected)
    turnaround_score = score  # Start with base score
    if capitulation_detected:
        bonus = TRADE_CAPITULATION_BONUS
        if resilience_count >= RESILIENCE_HIGH:
            bonus = int(bonus * RESILIENCE_MULTIPLIER_HIGH)
        turnaround_score += bonus
    elif post_shock_detected:
        bonus = TRADE_POST_SHOCK_BONUS
        if resilience_count >= RESILIENCE_HIGH:
            bonus = int(bonus * RESILIENCE_MULTIPLIER_HIGH)
        turnaround_score += bonus

    if cheap_winner_detected:
        turnaround_score += TRADE_CHEAP_WINNER_BONUS

    # Calculate BAU score (uses post-shock bonus, not capitulation)
    bau_score = score  # Start with base score
    if post_shock_detected:
        bonus = TRADE_POST_SHOCK_BONUS
        if resilience_count >= RESILIENCE_HIGH:
            bonus = int(bonus * RESILIENCE_MULTIPLIER_HIGH)
        bau_score += bonus

    if cheap_winner_detected:
        bau_score += TRADE_CHEAP_WINNER_BONUS

    # Check if turnaround mode is active
    # Active when: Capitulation detected AND price still below SMA(50)
    turnaround_active = capitulation_detected and (sma50 is not None and current_price < sma50)

    # Normalize both scores to 0-100 scale (v1.3 max points: 395)
    turnaround_normalized = normalize_score(turnaround_score, max_points=395)
    bau_normalized = normalize_score(bau_score, max_points=395)

    return ScoreResult(
        turnaround_raw=turnaround_score,
        turnaround_score=turnaround_normalized,
        bau_raw=bau_score,
        bau_score=bau_normalized,
        turnaround_active=turnaround_active
    )


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
) -> ScoreResult:
    """
    Calculate Investment Score (0-100) for innovation growth company quality (v1.4).

    Measures "Is this a quality growth stock worth holding through volatility?"
    Targets: NVDA (core), RKLB (growth), IONQ (satellite), space/quantum/AI innovation plays.

    Key differentiators from Trade Score:
    - Trade asks: "Is this good TIMING?" (momentum, entry precision)
    - Investment asks: "Is this a QUALITY GROWTH company?" (resilience, explosive upside)

    Args:
        current_price: Current stock price
        closes: Price history (required for v1.4 growth metrics)
        long_term_trend: 100-day trend bias
        volatility_bias: Volatility indicator bias
        resilience_count: Number of recovery patterns (CRITICAL in v1.4)
        sma50, sma100: Long-term moving averages
        distance_from_high: % below 20-day high
        Other params: Used for pattern detection

    Returns:
        ScoreResult with turnaround and BAU scores
    """
    # Import v1.4 growth indicators
    from .indicators import (
        compute_rally_magnitude,
        compute_growth_rate,
        compute_return_to_highs_frequency,
        compute_trend_slope
    )

    score = 0

    # ========================================================================
    # BASE SCORE (~90 points) - Innovation Growth Foundations
    # ========================================================================

    # 1. Long-Term Trend (100d): 25 points
    if long_term_trend == TrendBias.UP:
        score += 25
    elif long_term_trend == TrendBias.DOWN:
        score -= 25

    # 2. Resilience: 35 points (CRITICAL - 10x weight increase from v1.3)
    # Separates real innovation companies from pump-and-dumps
    if resilience_count >= 5:
        score += 35
    elif resilience_count >= 3:
        score += 25
    elif resilience_count >= 1:
        score += 15

    # 3. Growth Rate (1yr): 30 points
    if closes and len(closes) >= 252:
        growth_rate = compute_growth_rate(closes, 252)
        if growth_rate is not None:
            if growth_rate >= 100:
                score += 30
            elif growth_rate >= 50:
                score += 20
            elif growth_rate >= 20:
                score += 10
            elif growth_rate > 0:
                score += 5
            else:
                score -= 15  # Penalize negative growth

    # ========================================================================
    # GROWTH QUALITY BONUSES (~200 points) - Innovation Characteristics
    # ========================================================================

    # 1. Rally Magnitude: up to +50
    # Measures explosive upside capability (IONQ +900%, NVDA +200% years)
    if closes:
        rally_magnitude = compute_rally_magnitude(closes, 90)
        if rally_magnitude is not None:
            if rally_magnitude >= 100:
                score += 50
            elif rally_magnitude >= 50:
                score += 30
            elif rally_magnitude >= 30:
                score += 15

    # 2. Return to Highs Frequency: up to +40
    # Measures "winners stay winning" - quality stocks return to highs
    if closes:
        return_to_highs = compute_return_to_highs_frequency(closes, 180)
        if return_to_highs is not None:
            if return_to_highs >= 50:
                score += 40
            elif return_to_highs >= 30:
                score += 20

    # 3. Trend Slope (steepness): up to +30
    # Steeper uptrends = higher growth rate
    if closes:
        trend_slope = compute_trend_slope(closes, 100)
        if trend_slope is not None:
            if trend_slope >= 100:
                score += 30
            elif trend_slope >= 50:
                score += 20
            elif trend_slope >= 20:
                score += 10

    # 4. Volatility + Resilience Combo: +25
    # High volatility is OK if stock recovers (innovation growth characteristic)
    if volatility_bias == VolatilityBias.WILD and resilience_count >= 3:
        score += 25

    # 5. Winner's Premium: +40 (v1.4.1)
    # Rewards consistent excellence - stocks that stay near highs AND are battle-tested
    # Differentiates "superstar" (MU: 85% near highs, 3 recoveries) from "momentum spike"
    if closes:
        return_to_highs = compute_return_to_highs_frequency(closes, 180)
        if return_to_highs is not None and return_to_highs >= 80 and resilience_count >= 3:
            score += 40

    # ========================================================================
    # PATTERN BONUSES (~135 points) - Opportunity Detection (keep v1.3 logic)
    # ========================================================================

    capitulation_detected = detect_proven_winner_capitulation(
        current_price, closes, sma100, rsi_value, distance_from_high
    )
    post_shock_detected = detect_post_shock_recovery(
        current_price, distance_from_high, rsi_value, macd_hist, long_term_trend,
        closes=closes, sma100=sma100
    )
    cheap_winner_detected = detect_cheap_on_winner(
        current_price, sma20, sma100, long_term_trend, rsi_value
    )

    # Calculate TURNAROUND score (uses capitulation bonus)
    turnaround_score = score
    if capitulation_detected:
        bonus = 60  # INV_CAPITULATION_BONUS
        if resilience_count >= 3:
            bonus = int(bonus * 1.2)
        turnaround_score += bonus
    elif post_shock_detected:
        bonus = 60  # INV_POST_SHOCK_BONUS
        if resilience_count >= 3:
            bonus = int(bonus * 1.2)
        turnaround_score += bonus

    if cheap_winner_detected:
        turnaround_score += 15  # INV_CHEAP_WINNER_BONUS

    # Calculate BAU score (post-shock only, not capitulation)
    bau_score = score
    if post_shock_detected:
        bonus = 60
        if resilience_count >= 3:
            bonus = int(bonus * 1.2)
        bau_score += bonus

    if cheap_winner_detected:
        bau_score += 15

    # Turnaround active if capitulation detected AND price < SMA(50)
    turnaround_active = capitulation_detected and (sma50 is not None and current_price < sma50)

    # Normalize to 0-100 scale (v1.4.1 max points: ~465 with Winner's Premium)
    turnaround_normalized = normalize_score(turnaround_score, max_points=465)
    bau_normalized = normalize_score(bau_score, max_points=465)

    return ScoreResult(
        turnaround_raw=turnaround_score,
        turnaround_score=turnaround_normalized,
        bau_raw=bau_score,
        bau_score=bau_normalized,
        turnaround_active=turnaround_active
    )


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

    Score ranges (v1.4.1):
    - 80-100: STRONG BUY (lowered from 85 to reflect quality superstars like MU)
    - 70-79: BUY
    - 55-69: OUTPERFORM
    - 45-54: HOLD
    - 30-44: UNDERPERFORM
    - 0-29: SELL

    Args:
        score: Normalized score (0-100)

    Returns:
        Rating label string
    """
    if score >= 80:
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
