"""
Iceberg Score System - Dual-score rating for stocks

This module implements the proprietary Iceberg Score calculation,
which provides two perspectives on stock signals:
- Trade Score: Short-term entry timing (days/weeks)
- Investment Score: Long-term quality assessment (months/years)

See docs/SCORES_2.0_PLAN.md for full methodology documentation.

Version: 2.0.0 (2025-12-26)
COMPLETE REBUILD - Independent dual-score system

Trade Score (Short-term entry timing):
- Identifies swing trade opportunities (dip/recovery + momentum plays)
- Tiered momentum detection (3d/5d/8d)
- Tiered overbought penalties (RSI 65+/70+)
- Tiered parabolic top penalties (25%/30%/40%+ above SMA100)
- Validated via backtesting (ORCL, ASTS, MU, etc.)

Investment Score (Long-term quality assessment):
- Identifies quality growth stocks for long-term holding
- Growth-focused with 6 granular tiers (0%/10%/20%/30%/50%/100%+)
- Bottom confirmation for conservative entry
- Volatility awareness (prefer calm/choppy, penalize wild)
- Structural decline detection (-30% slope, negative growth)
- Scaled scoring to use full 0-100 range effectively
- Validated across spectrum (MU/GOOGL=100, MSFT=82, META=58, IBIT=34)
"""

from typing import Optional, List
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
# TRADE SCORE - Short-term entry timing (days/weeks)
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
    closes: Optional[List[float]] = None,
    support: Optional[float] = None,
    resistance: Optional[float] = None
) -> ScoreResult:
    """
    Calculate Trade Score for short-term trading signals (days/weeks).

    PURPOSE: Identify good entry points for swing trades
    TIME HORIZON: Days to weeks
    FOCUS: Momentum, timing, short-term technicals

    Identifies two types of opportunities:
    - Type 1: Dip/Recovery Plays (buy weakness)
    - Type 2: Momentum/Breakout Plays (buy strength)

    Args:
        All technical indicators available

    Returns:
        ScoreResult with scores 0-100
    """
    score = 50  # Start neutral

    if closes is None or len(closes) < 10:
        # Insufficient data - return neutral
        return ScoreResult(
            turnaround_raw=score,
            turnaround_score=score,
            bau_raw=score,
            bau_score=score,
            turnaround_active=False
        )

    # ========================================================================
    # TYPE 1: DIP/RECOVERY PLAYS (buy weakness)
    # ========================================================================

    # Detect sharp drop (-8%+ in 5 days) on stock with long-term uptrend
    if len(closes) >= 5:
        five_day_change = ((closes[-1] - closes[-5]) / closes[-5]) * 100
        if five_day_change <= -8 and long_term_trend == TrendBias.UP:
            score += 20  # Sharp drop on upward-trending stock

    # High resilience count (3+ historical recoveries)
    # Only reward resilience if not in long-term decline
    # (bounces in a downtrend aren't real recovery opportunities)
    if resilience_count >= 3 and long_term_trend != TrendBias.DOWN:
        score += 15  # Proven bounce-back ability

    # Pullback from high (-10% to -25% off high)
    # Only reward pullbacks on upward-trending or sideways stocks
    if distance_from_high is not None and long_term_trend != TrendBias.DOWN:
        if -25 <= distance_from_high <= -10:
            score += 10  # Sweet spot pullback

    # Below SMA(10) or SMA(20) but 50-day trend still up
    below_sma10 = sma10 is not None and current_price < sma10
    below_sma20 = sma20 is not None and current_price < sma20
    if (below_sma10 or below_sma20) and trend50_bias == TrendBias.UP:
        score += 15  # Dip on uptrending stock

    # RSI oversold (< 35) - potential bounce
    if rsi_value is not None and rsi_value < 35:
        score += 12  # Oversold - potential bounce

    # RSI overbought (tiered penalties for extended stocks)
    if rsi_value is not None:
        if rsi_value >= 70:
            score -= 12  # Overbought - very extended
        elif rsi_value >= 65:
            score -= 8  # Approaching overbought - getting risky

    # ========================================================================
    # TYPE 2: MOMENTUM/BREAKOUT PLAYS (buy strength)
    # ========================================================================

    # Strong 50-day uptrend
    if trend50_bias == TrendBias.UP:
        score += 15  # Solid upward trajectory

    # MACD bullish
    if macd_bias == MACDBias.BULL:
        score += 12  # Bullish momentum

    # Above SMA(20) and rising (trend10 up)
    above_sma20 = sma20 is not None and current_price > sma20
    if above_sma20 and trend10_bias == TrendBias.UP:
        score += 10  # Riding the trend

    # Tiered momentum detection (cumulative bonuses for strong recoveries)
    # 3% in 3 days: early momentum
    if len(closes) >= 3:
        three_day_gain = ((closes[-1] - closes[-3]) / closes[-3]) * 100
        if three_day_gain >= 3:
            score += 3  # Early momentum

    # 5% in 5 days: building momentum
    if len(closes) >= 5:
        five_day_gain = ((closes[-1] - closes[-5]) / closes[-5]) * 100
        if five_day_gain >= 5:
            score += 3  # Building momentum (cumulative)

    # 10% in 8 days: strong recovery/momentum signal
    if len(closes) >= 8:
        eight_day_gain = ((closes[-1] - closes[-8]) / closes[-8]) * 100
        if eight_day_gain >= 10:
            score += 6  # Strong recovery (cumulative)

    # ========================================================================
    # SUPPORT/RESISTANCE CONSIDERATIONS
    # ========================================================================

    # Near support = good bounce opportunity (within 5% of support)
    if support and current_price <= support * 1.05:
        score += 10  # At support - good entry for bounce

    # Just broke above resistance = breakout momentum (0-3% above)
    if resistance and current_price > resistance and current_price <= resistance * 1.03:
        score += 12  # Fresh breakout - momentum trade

    # Near resistance = caution (within 5% below resistance, likely rejection)
    if resistance and current_price >= resistance * 0.95 and current_price < resistance:
        score -= 8  # Near ceiling - risky entry

    # Room to run = better risk/reward (>10% upside to resistance)
    if support and resistance:
        upside_room = ((resistance - current_price) / current_price) * 100
        if upside_room > 10:
            score += 5  # >10% room to resistance

    # ========================================================================
    # CAUTION FLAGS (light penalties)
    # ========================================================================

    # Severe extended drop (> -40% from high) - might be structural
    if distance_from_high is not None and distance_from_high < -40:
        score -= 15

    # Long-term downtrend (50-day) - weaker setup
    if trend50_bias == TrendBias.DOWN:
        score -= 10

    # Very extended rally (> +40% in 10 days) - might be overheating
    if len(closes) >= 10:
        ten_day_change = ((closes[-1] - closes[-10]) / closes[-10]) * 100
        if ten_day_change > 40:
            score -= 8

    # Structural decline - severe long-term deterioration
    # Check trend slope to catch gradual but persistent decline
    if len(closes) >= 100:
        from .indicators import compute_trend_slope
        trend_slope = compute_trend_slope(closes, 100)
        if trend_slope is not None and trend_slope < -30:
            score -= 15  # Severe structural decline

    # Parabolic top - tiered penalties for extension above SMA(100)
    # Catches dangerous "too far, too fast" setups
    if sma100 is not None and current_price > sma100:
        extension_pct = ((current_price - sma100) / sma100) * 100
        if extension_pct >= 40:
            score -= 30  # Extremely parabolic - very high risk
        elif extension_pct >= 30:
            score -= 20  # Severely extended - high risk
        elif extension_pct >= 25:
            score -= 10  # Getting extended - elevated risk

    # Clamp score to 0-100
    score = max(0, min(100, score))

    return ScoreResult(
        turnaround_raw=score,
        turnaround_score=score,
        bau_raw=score,
        bau_score=score,
        turnaround_active=False
    )


# ============================================================================
# INVESTMENT SCORE - Long-term quality assessment (months/years)
# ============================================================================

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
    Calculate Investment Score for long-term quality assessment (months/years).

    PURPOSE: Identify quality growth stocks worth holding long-term
    TIME HORIZON: Months to years
    FOCUS: Growth trajectory, resilience, acceptable volatility, company strength

    Philosophy: Conservative, quality-focused. Wait for bottom confirmation,
    favor low volatility and strong growth trajectory. Less risky than trades.

    Examples:
    - GOOGL/MSFT: Growth ~30%, low vol, resilient → ~85 (STRONG BUY)
    - RKLB: Growth ~70%, high vol BUT resilient, rally >100% → ~70 (BUY)
    - IBIT: Negative growth, declining, high vol → ~25 (SELL)

    Args:
        All technical indicators available

    Returns:
        ScoreResult with scores 0-100
    """
    score = 50  # Start neutral

    if closes is None or len(closes) < 100:
        # Insufficient data - return neutral
        return ScoreResult(
            turnaround_raw=score,
            turnaround_score=score,
            bau_raw=score,
            bau_score=score,
            turnaround_active=False
        )

    # Import long-term indicator functions
    from .indicators import (
        compute_growth_rate,
        compute_trend_slope,
        compute_rally_magnitude,
        compute_return_to_highs_frequency
    )

    # Calculate long-term indicators
    trend_slope = compute_trend_slope(closes, 100)
    rally_magnitude = compute_rally_magnitude(closes, 90)
    return_to_highs = compute_return_to_highs_frequency(closes, 180)

    # Calculate growth rate with tiered bonuses based on period
    growth_rate = None
    growth_period = None
    if len(closes) >= 252:
        growth_rate = compute_growth_rate(closes, 252)
        growth_period = 12  # months
    elif len(closes) >= 189:
        growth_rate = compute_growth_rate(closes, 189)
        growth_period = 9  # months
    elif len(closes) >= 126:
        growth_rate = compute_growth_rate(closes, 126)
        growth_period = 6  # months

    # ========================================================================
    # GROWTH & TRAJECTORY (primary signals)
    # ========================================================================

    # Growth rate with tiered bonuses (12mo > 9mo > 6mo)
    # Growth is the primary objective of investing - penalize very low growth
    if growth_rate is not None and growth_period is not None:
        if growth_period == 12:
            # 12-month growth: Full bonuses
            if growth_rate > 100:
                score += 18  # Exceptional growth (MU, RKLB)
            elif growth_rate > 50:
                score += 15  # Very strong growth (GOOGL)
            elif growth_rate > 30:
                score += 12  # Strong growth (NVDA)
            elif growth_rate > 20:
                score += 9   # Good growth
            elif growth_rate > 10:
                score += 6   # Moderate growth (MSFT)
            elif growth_rate > 5:
                score += 0   # Minimal growth - neutral (AAPL)
            elif growth_rate > 0:
                score -= 5   # Very low growth (AMZN)
        elif growth_period == 9:
            # 9-month growth: Slightly reduced (~85% of 12-month)
            if growth_rate > 100:
                score += 15
            elif growth_rate > 50:
                score += 12
            elif growth_rate > 30:
                score += 10
            elif growth_rate > 20:
                score += 7
            elif growth_rate > 10:
                score += 5
            elif growth_rate > 5:
                score += 0
            elif growth_rate > 0:
                score -= 4
        elif growth_period == 6:
            # 6-month growth: Further reduced (~67% of 12-month)
            if growth_rate > 100:
                score += 12
            elif growth_rate > 50:
                score += 10
            elif growth_rate > 30:
                score += 8
            elif growth_rate > 20:
                score += 6
            elif growth_rate > 10:
                score += 4
            elif growth_rate > 5:
                score += 0
            elif growth_rate > 0:
                score -= 3

    # Trend slope - long-term trajectory steepness
    if trend_slope is not None:
        if trend_slope > 30:
            score += 9   # Steep upward trajectory (was +15)
        elif trend_slope > 10:
            score += 6   # Solid upward trajectory (was +10)

    # Long-term trend (100-day) - structural uptrend
    if long_term_trend == TrendBias.UP:
        score += 9   # Strong structural uptrend (was +15)

    # ========================================================================
    # QUALITY & RESILIENCE (company strength)
    # ========================================================================

    # Resilience - proven bounce-back ability
    if resilience_count >= 3:
        score += 9   # High resilience, recovers well (was +15)

    # Return to highs frequency - consistency
    if return_to_highs is not None and return_to_highs > 50:
        score += 6   # Spends >50% of time near highs (was +10)

    # Rally magnitude - historical upside potential
    if rally_magnitude is not None:
        if rally_magnitude > 100:
            score += 6   # Explosive upside (was +10)
        elif rally_magnitude > 50:
            score += 3   # Strong upside potential (was +5)

    # ========================================================================
    # VOLATILITY (risk awareness - prefer lower but not disqualifying)
    # ========================================================================

    # Tiered volatility penalties to differentiate risk levels
    # Use raw sigma value for more granular assessment
    if volatility_bias == VolatilityBias.CALM:
        score += 6   # Ideal for long-term comfort
    elif volatility_bias == VolatilityBias.CHOPPY:
        score += 2   # Acceptable volatility
    elif volatility_bias == VolatilityBias.WILD:
        # Wild volatility (>3%) - tiered penalties based on severity
        # Calculate approximate sigma from closes for finer granularity
        from .indicators import compute_volatility
        vol_result = compute_volatility(closes)
        if vol_result and vol_result.sigma > 10:
            score -= 15  # Extremely wild (>10% daily sigma)
        elif vol_result and vol_result.sigma > 5:
            score -= 10  # Very wild (5-10% daily sigma)
        else:
            score -= 5   # Wild (3-5% daily sigma)

    # ========================================================================
    # BOTTOM CONFIRMATION (conservative entry)
    # ========================================================================

    # RSI - not in freefall
    if rsi_value is not None and rsi_value > 40:
        score += 6   # Not oversold/crashing (was +10)

    # Price holding above recent low (5-day stabilization)
    if len(closes) >= 5:
        five_day_low = min(closes[-5:])
        if current_price >= five_day_low:
            score += 3   # Holding above recent low (was +5)

    # Above SMA(100) - long-term support intact
    if sma100 is not None and current_price > sma100:
        score += 6   # Above long-term average (was +10)

    # ========================================================================
    # STRUCTURAL DECLINE (major penalties)
    # ========================================================================

    # Severe slope decline - structural deterioration
    if trend_slope is not None and trend_slope < -30:
        score -= 24  # Severe structural decline (was -40)

    # Negative 1-year growth - declining not growing
    if growth_rate is not None and growth_rate < 0:
        score -= 12  # Negative growth trajectory (was -20)

    # No resilience history - unproven recovery ability
    if resilience_count == 0:
        score -= 6   # Never recovered from dips (was -10)

    # Very extended drop - might be structural
    if distance_from_high is not None and distance_from_high < -40:
        score -= 12  # Severe drop from highs (was -20)

    # Clamp score to 0-100
    score = max(0, min(100, score))

    return ScoreResult(
        turnaround_raw=score,
        turnaround_score=score,
        bau_raw=score,
        bau_score=score,
        turnaround_active=False
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_rating_label(score: int, is_trade_score: bool = False) -> str:
    """
    Convert numeric score to categorical rating.

    Trade Score ranges (aggressive - identifies entry points):
    - 75-100: STRONG BUY
    - 65-74: BUY
    - 55-64: OUTPERFORM
    - 45-54: HOLD
    - 30-44: UNDERPERFORM
    - 0-29: SELL

    Investment Score ranges (selective - quality long-term):
    - 85-100: STRONG BUY (only exceptional)
    - 60-84: BUY (good stocks worth buying)
    - 45-59: HOLD
    - 30-44: UNDERPERFORM
    - 0-29: SELL

    Args:
        score: Normalized score (0-100)
        is_trade_score: True for Trade Score (lower thresholds), False for Investment Score

    Returns:
        Rating label string
    """
    if is_trade_score:
        # Trade Score: Lower thresholds for more aggressive entry signals
        if score >= 75:
            return "STRONG BUY"
        elif score >= 65:
            return "BUY"
        elif score >= 55:
            return "OUTPERFORM"
        elif score >= 45:
            return "HOLD"
        elif score >= 30:
            return "UNDERPERFORM"
        else:
            return "SELL"
    else:
        # Investment Score: Higher thresholds for selectivity (only exceptional = STRONG BUY)
        if score >= 85:
            return "STRONG BUY"
        elif score >= 60:
            return "BUY"
        elif score >= 45:
            return "HOLD"
        elif score >= 30:
            return "UNDERPERFORM"
        else:
            return "SELL"


def get_rating_color(score: int) -> str:
    """
    Get color for score/rating display.

    Aligned with Trade Score rating thresholds:
    - 75+: STRONG BUY (bright green)
    - 65-74: BUY (green)
    - 55-64: OUTPERFORM (yellow-green)
    - 45-54: HOLD (gray)
    - 30-44: UNDERPERFORM (orange)
    - <30: SELL (red)

    Args:
        score: Normalized score (0-100)

    Returns:
        Color code string
    """
    if score >= 75:
        return "#00ff00"  # Bright green - STRONG BUY
    elif score >= 65:
        return "#88ff00"  # Green - BUY
    elif score >= 55:
        return "#ccff00"  # Yellow-green - OUTPERFORM
    elif score >= 45:
        return "#888888"  # Gray - HOLD
    elif score >= 30:
        return "#ffaa00"  # Orange - UNDERPERFORM
    else:
        return "#ff0000"  # Red - SELL/AVOID


def generate_score_bar(score: int, width: int = 20) -> str:
    """
    Generate ASCII bar chart for score visualization.

    Args:
        score: Score value (0-100)
        width: Width of bar in characters

    Returns:
        ASCII bar string
    """
    filled = int((score / 100) * width)
    empty = width - filled
    return "█" * filled + "░" * empty
