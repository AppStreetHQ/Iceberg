"""Technical analysis panel widget"""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Static
from typing import Optional

from ..data.db import Database
from ..analysis.indicators import (
    compute_macd,
    compute_rsi,
    compute_sma,
    compute_trend,
    compute_volatility,
)
from ..analysis.models import MACDBias, RSIBias, TrendBias, VolatilityBias


class TechnicalPanel(Widget):
    """Technical analysis indicators display"""

    def __init__(self, db: Database, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = db
        self.current_ticker: Optional[str] = None
        self.current_range: int = 30

    def compose(self) -> ComposeResult:
        """Compose technical panel"""
        with VerticalScroll(id="technical_container"):
            yield Static("Select a ticker to view analysis", id="technical_display")

    def update_ticker(self, ticker: str, day_range: Optional[int] = None) -> None:
        """Update analysis for new ticker"""
        self.current_ticker = ticker
        if day_range is not None:
            self.current_range = day_range
        self.render_analysis()

    def update_range(self, day_range: int) -> None:
        """Update day range"""
        self.current_range = day_range
        if self.current_ticker:
            self.render_analysis()

    def render_analysis(self) -> None:
        """Render technical analysis"""
        if not self.current_ticker:
            return

        # Fetch closing prices - use more data for better indicator calculation
        # but limit to max of 365 days to avoid performance issues
        data_days = min(self.current_range + 100, 365)
        closes = self.db.get_closing_prices(self.current_ticker, data_days)

        if not closes or len(closes) < 20:
            self.query_one("#technical_display", Static).update(
                f"Insufficient data for {self.current_ticker} technical analysis"
            )
            return

        # Compute indicators
        macd = compute_macd(closes)
        rsi = compute_rsi(closes, 14)
        sma20 = compute_sma(closes, 20)
        trend = compute_trend(closes, 20)
        volatility = compute_volatility(closes)

        # Build display
        lines = [f"═══ {self.current_ticker} Technical Analysis ═══\n"]

        # MACD
        if macd:
            emoji = "🐂" if macd.bias == MACDBias.BULL else "🐻" if macd.bias == MACDBias.BEAR else "➡️"
            lines.append(
                f"MACD(12,26,9):   {emoji} {macd.bias.value.title()} "
                f"(MACD {macd.macd:.2f}, Signal {macd.signal:.2f}, Hist {macd.hist:.2f})"
            )
        else:
            lines.append("MACD(12,26,9):   N/A")

        # RSI
        if rsi:
            emoji_map = {
                RSIBias.OVERBOUGHT: "🔴",
                RSIBias.STRONG: "🟢",
                RSIBias.NEUTRAL: "🟡",
                RSIBias.WEAK: "🟠",
                RSIBias.OVERSOLD: "🔵",
            }
            emoji = emoji_map.get(rsi.bias, "⚪")
            lines.append(f"RSI(14):         {emoji} {rsi.value:.1f} - {rsi.bias.value.title()}")
        else:
            lines.append("RSI(14):         N/A")

        # SMA
        if sma20:
            lines.append(f"SMA(20):         ${sma20:.2f}")
        else:
            lines.append("SMA(20):         N/A")

        # Trend
        if trend:
            emoji = "🟢" if trend.bias == TrendBias.UP else "🔴" if trend.bias == TrendBias.DOWN else "🟡"
            direction = "Up" if trend.bias == TrendBias.UP else "Down" if trend.bias == TrendBias.DOWN else "Sideways"
            lines.append(
                f"Trend:           {emoji} {direction} "
                f"(Last vs SMA: {trend.delta_pct:+.2f}%)"
            )
        else:
            lines.append("Trend:           N/A")

        # Volatility
        if volatility:
            emoji_map = {
                VolatilityBias.CALM: "🟢",
                VolatilityBias.CHOPPY: "🟠",
                VolatilityBias.WILD: "🔴",
            }
            emoji = emoji_map.get(volatility.bias, "⚪")
            lines.append(
                f"Volatility (σ):  {emoji} {volatility.bias.value.title()} "
                f"(daily σ = {volatility.sigma:.2f}%)"
            )
        else:
            lines.append("Volatility (σ):  N/A")

        # Direction today
        if len(closes) >= 2:
            today = closes[-1]
            yesterday = closes[-2]
            change = today - yesterday
            if change > 0:
                direction_emoji = "⬆️"
                direction_text = "Climbing"
            elif change < 0:
                direction_emoji = "⬇️"
                direction_text = "Falling"
            else:
                direction_emoji = "➡️"
                direction_text = "Flat"

            lines.append(
                f"Direction today: {direction_emoji}  {direction_text} "
                f"(${change:+.2f} vs yesterday)"
            )

        display_text = "\n".join(lines)
        self.query_one("#technical_display", Static).update(display_text)
