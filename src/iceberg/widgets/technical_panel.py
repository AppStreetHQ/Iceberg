"""Technical analysis panel widget"""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Static
from typing import Optional
from rich.text import Text

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
        self.last_analysis_text: Optional[str] = None

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

    def get_analysis_text(self) -> Optional[str]:
        """Get the current analysis text for export"""
        return self.last_analysis_text

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
        trend20 = compute_trend(closes, 20)
        trend_range = compute_trend(closes, min(len(closes), self.current_range))
        volatility = compute_volatility(closes)

        # Pattern-based rating using indicator combinations
        macd_bull = macd and macd.bias == MACDBias.BULL
        macd_bear = macd and macd.bias == MACDBias.BEAR
        trend_up = trend20 and trend20.bias == TrendBias.UP
        trend_down = trend20 and trend20.bias == TrendBias.DOWN
        trend_sideways = trend20 and trend20.bias == TrendBias.SIDEWAYS
        rsi_overbought = rsi and rsi.bias == RSIBias.OVERBOUGHT
        rsi_oversold = rsi and rsi.bias == RSIBias.OVERSOLD
        rsi_strong = rsi and rsi.bias == RSIBias.STRONG
        rsi_weak = rsi and rsi.bias == RSIBias.WEAK
        price_above_sma = sma20 and closes and closes[-1] > sma20
        price_below_sma = sma20 and closes and closes[-1] < sma20

        # Strong Buy: All bullish signals aligned
        if (macd_bull and trend_up and price_above_sma and (rsi_strong or rsi_oversold)):
            rating = "STRONG BUY"
            rating_color = "#00ff00"

        # Buy: Strong bullish momentum
        elif (macd_bull and trend_up) or \
             (macd_bull and price_above_sma and not rsi_overbought) or \
             (trend_up and rsi_oversold and price_above_sma):
            rating = "BUY"
            rating_color = "#00ff00"

        # Outperform: Leaning bullish but not all signals
        elif (macd_bull and trend_sideways) or \
             (trend_up and not macd_bear) or \
             (price_above_sma and macd_bull) or \
             (price_above_sma and trend_up and not macd_bear):
            rating = "OUTPERFORM"
            rating_color = "#88ff88"

        # Sell: Strong bearish momentum
        elif (macd_bear and trend_down) or \
             (macd_bear and price_below_sma and not rsi_oversold) or \
             (trend_down and rsi_overbought and price_below_sma):
            rating = "SELL"
            rating_color = "#ff0000"

        # Underperform: Leaning bearish but not all signals
        elif (macd_bear and trend_sideways) or \
             (trend_down and not macd_bull) or \
             (price_below_sma and macd_bear) or \
             (price_below_sma and trend_down and not macd_bull):
            rating = "UNDERPERFORM"
            rating_color = "#ff8888"

        # Hold: Mixed or neutral signals
        else:
            rating = "HOLD"
            rating_color = "#888888"

        # Build display using Text object for consistent rendering
        display = Text()

        # Title
        display.append(f"{self.current_ticker} - Technical Analysis", style="bold bright_white")
        display.append("\n\n")

        # Rating
        display.append("Rating: ")
        display.append(rating, style=rating_color)
        display.append("\n\n")

        # MACD
        if macd:
            emoji = "🐂" if macd.bias == MACDBias.BULL else "🐻" if macd.bias == MACDBias.BEAR else "➡️"
            color = "#00ff00" if macd.bias == MACDBias.BULL else "#ff0000" if macd.bias == MACDBias.BEAR else "#888888"
            display.append("MACD(12,26,9):   ")
            display.append(f"{emoji} ", style=color)
            display.append(macd.bias.value.title(), style=color)
            display.append(f" (MACD {macd.macd:.2f}, Signal {macd.signal:.2f}, Hist {macd.hist:.2f})\n")
        else:
            display.append("MACD(12,26,9):   N/A\n")

        # RSI
        if rsi:
            emoji_map = {
                RSIBias.OVERBOUGHT: "🔴",
                RSIBias.STRONG: "🟢",
                RSIBias.NEUTRAL: "🟡",
                RSIBias.WEAK: "🟠",
                RSIBias.OVERSOLD: "🔵",
            }
            color_map = {
                RSIBias.OVERBOUGHT: "#ff0000",
                RSIBias.STRONG: "#00ff00",
                RSIBias.NEUTRAL: "#888888",
                RSIBias.WEAK: "#ffaa00",
                RSIBias.OVERSOLD: "#0088ff",
            }
            emoji = emoji_map.get(rsi.bias, "⚪")
            color = color_map.get(rsi.bias, "#888888")
            display.append("RSI(14):         ")
            display.append(f"{emoji} ", style=color)
            display.append(f"{rsi.value:.1f}", style=color)
            display.append(f" - {rsi.bias.value.title()}\n")
        else:
            display.append("RSI(14):         N/A\n")

        display.append("\n")  # Spacing

        # SMA(20) - fixed 20-day period
        if sma20 and closes:
            current_price = closes[-1]
            sma20_diff_pct = ((current_price - sma20) / sma20) * 100 if sma20 != 0 else 0

            if current_price > sma20:
                sma_emoji = "🟢"
                sma_color = "#00ff00"
            else:
                sma_emoji = "🔴"
                sma_color = "#ff0000"

            display.append("SMA(20):         ")
            display.append(f"{sma_emoji} ", style=sma_color)
            display.append(f"${sma20:.2f} ", style=sma_color)
            display.append(f"({sma20_diff_pct:+.2f}%)", style=sma_color)
            display.append("\n")

            # Trend for SMA(20)
            if trend20:
                trend_color = "#00ff00" if trend20.bias == TrendBias.UP else "#ff0000" if trend20.bias == TrendBias.DOWN else "#888888"
                trend_direction = "Up" if trend20.bias == TrendBias.UP else "Down" if trend20.bias == TrendBias.DOWN else "Sideways"
                display.append("  Trend:         ")
                display.append(trend_direction, style=trend_color)
                display.append(" (vs SMA(20): ")
                display.append(f"{trend20.delta_pct:+.2f}%", style=trend_color)
                display.append(")\n")
            else:
                display.append("  Trend:         N/A\n")
        else:
            display.append("SMA(20):         N/A\n")

        display.append("\n")  # Spacing between SMAs

        # SMA(range) - dynamic based on selected range
        if closes and len(closes) >= 2:
            current_price = closes[-1]
            sma_range = compute_sma(closes, len(closes))

            if sma_range:
                sma_range_diff_pct = ((current_price - sma_range) / sma_range) * 100 if sma_range != 0 else 0

                if current_price > sma_range:
                    sma_range_emoji = "🟢"
                    sma_range_color = "#00ff00"
                else:
                    sma_range_emoji = "🔴"
                    sma_range_color = "#ff0000"

                # Dynamically adjust spacing based on range value length
                range_label = f"SMA({self.current_range}):"
                padding = " " * (17 - len(range_label))  # Align to same position as SMA(20)

                display.append(range_label)
                display.append(padding)
                display.append(f"{sma_range_emoji} ", style=sma_range_color)
                display.append(f"${sma_range:.2f} ", style=sma_range_color)
                display.append(f"({sma_range_diff_pct:+.2f}%)", style=sma_range_color)
                display.append("\n")

                # Trend for SMA(range)
                if trend_range:
                    trend_color = "#00ff00" if trend_range.bias == TrendBias.UP else "#ff0000" if trend_range.bias == TrendBias.DOWN else "#888888"
                    trend_direction = "Up" if trend_range.bias == TrendBias.UP else "Down" if trend_range.bias == TrendBias.DOWN else "Sideways"
                    display.append("  Trend:         ")
                    display.append(trend_direction, style=trend_color)
                    display.append(f" (vs SMA({self.current_range}): ")
                    display.append(f"{trend_range.delta_pct:+.2f}%", style=trend_color)
                    display.append(")\n")
                else:
                    display.append("  Trend:         N/A\n")
            else:
                display.append(f"SMA({self.current_range}):       N/A\n")
        else:
            display.append(f"SMA({self.current_range}):       N/A\n")

        display.append("\n")  # Spacing

        # Volatility
        if volatility:
            color_map = {
                VolatilityBias.CALM: "#00ff00",
                VolatilityBias.CHOPPY: "#ffaa00",
                VolatilityBias.WILD: "#ff0000",
            }
            color = color_map.get(volatility.bias, "#888888")
            display.append("Volatility:      ")
            display.append(volatility.bias.value.title(), style=color)
            display.append(f" (daily σ = {volatility.sigma:.2f}%)\n")
        else:
            display.append("Volatility:      N/A\n")

        display.append("\n")  # Spacing

        # Last price change
        if len(closes) >= 2:
            today = closes[-1]
            yesterday = closes[-2]
            change = today - yesterday
            change_pct = (change / yesterday * 100) if yesterday != 0 else 0

            if change > 0:
                change_color = "#00ff00"
                arrow = "▲"
            elif change < 0:
                change_color = "#ff0000"
                arrow = "▼"
            else:
                change_color = "#888888"
                arrow = "→"

            display.append("Last Change:     ")
            display.append(f"{arrow} ${abs(change):.2f} ({change_pct:+.2f}%)", style=change_color)
            display.append("\n")

        # Store plain text for clipboard export
        self.last_analysis_text = display.plain

        # Update display with Text object
        self.query_one("#technical_display", Static).update(display)
