"""
Iceberg Score System - Dual-score rating for stocks

This module implements the proprietary Iceberg Score calculation,
which provides two perspectives on stock signals:
- Trade Score: Short-term entry timing (days/weeks)
- Investment Score: Long-term quality assessment (months/years)

See ICEBERG_INDEX.md for full methodology documentation.

Version: 2.0.0-dev (2025-12-26)
CLEAN REBUILD - Starting from scratch with independent scoring systems
- Trade and Investment scores built independently with separate logic
- Clear separation of concerns to avoid confusion
- Backtest infrastructure preserved from v1.4.x
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
    closes: Optional[List[float]] = None
) -> ScoreResult:
    """
    Calculate Trade Score for short-term trading signals (days/weeks).

    PURPOSE: Identify good entry points for swing trades
    TIME HORIZON: Days to weeks
    FOCUS: Momentum, timing, short-term technicals

    TODO: Build from scratch
    - Define clear objective
    - Choose relevant indicators (MACD, RSI, short-term trends)
    - Weight appropriately for short-term timing
    - Test and validate

    Args:
        All technical indicators available

    Returns:
        ScoreResult with scores 0-100
    """
    # STUB: Return neutral score until rebuilt
    score = 50

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
    FOCUS: Growth trajectory, resilience, long-term fundamentals

    TODO: Build from scratch
    - Define clear objective
    - Choose relevant indicators (growth, long-term trends, quality)
    - Weight appropriately for long-term holding
    - Test and validate

    Args:
        All technical indicators available

    Returns:
        ScoreResult with scores 0-100
    """
    # STUB: Return neutral score until rebuilt
    score = 50

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
    - 80-100: STRONG BUY
    - 70-79: BUY
    - 60-69: OUTPERFORM
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
        # Investment Score: Higher thresholds for selectivity
        if score >= 80:
            return "STRONG BUY"
        elif score >= 70:
            return "BUY"
        elif score >= 60:
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
        Color code string
    """
    if score >= 80:
        return "#00ff00"  # Bright green
    elif score >= 70:
        return "#88ff00"  # Green
    elif score >= 60:
        return "#ccff00"  # Yellow-green
    elif score >= 45:
        return "#888888"  # Gray
    elif score >= 30:
        return "#ffaa00"  # Orange
    else:
        return "#ff0000"  # Red


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
