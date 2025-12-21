"""Data models for technical analysis results"""

from dataclasses import dataclass
from enum import Enum


class MACDBias(Enum):
    """MACD trend bias"""

    BULL = "bull"
    BEAR = "bear"
    NEUTRAL = "neutral"


class RSIBias(Enum):
    """RSI strength bias"""

    OVERBOUGHT = "overbought"
    STRONG = "strong"
    NEUTRAL = "neutral"
    WEAK = "weak"
    OVERSOLD = "oversold"


class TrendBias(Enum):
    """Trend direction bias"""

    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways"


class VolatilityBias(Enum):
    """Volatility level bias"""

    CALM = "calm"
    CHOPPY = "choppy"
    WILD = "wild"


@dataclass
class MACDResult:
    """MACD indicator result"""

    macd: float
    signal: float
    hist: float
    bias: MACDBias


@dataclass
class RSIResult:
    """RSI indicator result"""

    value: float
    bias: RSIBias


@dataclass
class TrendSummary:
    """Trend analysis result"""

    sma_value: float
    delta_pct: float
    bias: TrendBias


@dataclass
class VolatilitySummary:
    """Volatility analysis result"""

    sigma: float
    bias: VolatilityBias
