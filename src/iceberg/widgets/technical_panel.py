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
    compute_distance_from_high,
    count_recovery_patterns,
    compute_long_term_trend,
)
from ..analysis.models import MACDBias, RSIBias, TrendBias, VolatilityBias
from ..analysis.scoring import (
    calculate_trade_score,
    calculate_investment_score,
    get_rating_label,
    get_rating_color,
    generate_score_bar,
)


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

        # Fetch closing prices - always use 365 days for consistent indicator calculation
        # MACD, RSI, SMAs should be calculated the same way regardless of selected range
        data_days = 365
        closes = self.db.get_closing_prices(self.current_ticker, data_days)

        if not closes or len(closes) < 20:
            self.query_one("#technical_display", Static).update(
                f"Insufficient data for {self.current_ticker} technical analysis"
            )
            return

        # Compute indicators
        current_price = closes[-1]
        macd = compute_macd(closes)
        rsi = compute_rsi(closes, 14)

        # SMAs for scoring and display
        sma10 = compute_sma(closes, 10)
        sma20 = compute_sma(closes, 20)
        sma50 = compute_sma(closes, 50)
        sma100 = compute_sma(closes, 100)

        # Trends for scoring and display
        trend10 = compute_trend(closes, 10)
        trend20 = compute_trend(closes, 20)
        trend50 = compute_trend(closes, 50)
        trend_range = compute_trend(closes, min(len(closes), self.current_range))
        long_term_trend = compute_long_term_trend(closes, 100)

        volatility = compute_volatility(closes)

        # v1.1 indicators
        distance_from_high = compute_distance_from_high(closes, 20)
        resilience_count = count_recovery_patterns(closes, 180)

        # Calculate Iceberg Scores (v1.3 - returns ScoreResult)
        trade_result = calculate_trade_score(
            current_price=current_price,
            macd_bias=macd.bias if macd else None,
            macd_hist=macd.hist if macd else None,
            rsi_value=rsi.value if rsi else None,
            rsi_bias=rsi.bias if rsi else None,
            sma10=sma10,
            sma20=sma20,
            sma50=sma50,
            sma100=sma100,
            trend10_bias=trend10.bias if trend10 else None,
            trend50_bias=trend50.bias if trend50 else None,
            long_term_trend=long_term_trend,
            volatility_bias=volatility.bias if volatility else None,
            distance_from_high=distance_from_high,
            resilience_count=resilience_count,
            closes=closes
        )

        inv_result = calculate_investment_score(
            current_price=current_price,
            macd_bias=macd.bias if macd else None,
            macd_hist=macd.hist if macd else None,
            rsi_value=rsi.value if rsi else None,
            rsi_bias=rsi.bias if rsi else None,
            sma10=sma10,
            sma20=sma20,
            sma50=sma50,
            sma100=sma100,
            trend10_bias=trend10.bias if trend10 else None,
            trend50_bias=trend50.bias if trend50 else None,
            long_term_trend=long_term_trend,
            volatility_bias=volatility.bias if volatility else None,
            distance_from_high=distance_from_high,
            resilience_count=resilience_count,
            closes=closes
        )

        # Build display using Text object for consistent rendering
        display = Text()

        # Title
        display.append(f"{self.current_ticker} - Technical Analysis", style="bold bright_white")
        display.append("\n\n")
        display.append("Iceberg™ Score System v1.4.2", style="#00ffff")
        display.append("\n\n")

        # Iceberg Scores - use display_score from ScoreResult
        trade_score = trade_result.display_score
        trade_label = get_rating_label(trade_score)
        trade_color = get_rating_color(trade_score)
        trade_bar = generate_score_bar(trade_score, width=20)

        inv_score = inv_result.display_score
        inv_label = get_rating_label(inv_score)
        inv_color = get_rating_color(inv_score)
        inv_bar = generate_score_bar(inv_score, width=20)

        # Add turnaround indicator if active
        trade_suffix = " ⚡" if trade_result.turnaround_active else ""
        inv_suffix = " ⚡" if inv_result.turnaround_active else ""

        display.append("Trade Score:      ", style="bold white")
        display.append(f"{trade_score}/100 ", style=trade_color)
        display.append(trade_bar, style=trade_color)
        display.append(f"  {trade_label}{trade_suffix}", style=trade_color)
        display.append("\n")

        display.append("Investment Score: ", style="bold white")
        display.append(f"{inv_score}/100 ", style=inv_color)
        display.append(inv_bar, style=inv_color)
        display.append(f"  {inv_label}{inv_suffix}", style=inv_color)
        display.append("\n")

        display.append("─" * 40, style="#333333")
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

        # SMAs - side by side to save space
        current_price = closes[-1] if closes else 0

        # SMA(20) data
        if sma20:
            sma20_diff_pct = ((current_price - sma20) / sma20) * 100 if sma20 != 0 else 0
            sma20_emoji = "🟢" if current_price > sma20 else "🔴"
            sma20_color = "#00ff00" if current_price > sma20 else "#ff0000"

            if trend20:
                trend20_direction = "Up" if trend20.bias == TrendBias.UP else "Down" if trend20.bias == TrendBias.DOWN else "Sideways"
                trend20_color = "#00ff00" if trend20.bias == TrendBias.UP else "#ff0000" if trend20.bias == TrendBias.DOWN else "#888888"
            else:
                trend20_direction = "N/A"
                trend20_color = "#888888"

        # SMA(range) data
        sma_range = compute_sma(closes, len(closes)) if closes and len(closes) >= 2 else None
        if sma_range:
            sma_range_diff_pct = ((current_price - sma_range) / sma_range) * 100 if sma_range != 0 else 0
            sma_range_emoji = "🟢" if current_price > sma_range else "🔴"
            sma_range_color = "#00ff00" if current_price > sma_range else "#ff0000"

            if trend_range:
                trend_range_direction = "Up" if trend_range.bias == TrendBias.UP else "Down" if trend_range.bias == TrendBias.DOWN else "Sideways"
                trend_range_color = "#00ff00" if trend_range.bias == TrendBias.UP else "#ff0000" if trend_range.bias == TrendBias.DOWN else "#888888"
            else:
                trend_range_direction = "N/A"
                trend_range_color = "#888888"

        # Display SMAs side by side
        if sma20:
            display.append("SMA(20): ", style="white")
            display.append(f"{sma20_emoji} ", style=sma20_color)
            display.append(f"${sma20:.2f} ({sma20_diff_pct:+.2f}%), ", style=sma20_color)
            display.append(trend20_direction, style=trend20_color)
        else:
            display.append("SMA(20): N/A", style="white")

        display.append("  │  ", style="#333333")

        if sma_range:
            display.append(f"SMA({self.current_range}): ", style="white")
            display.append(f"{sma_range_emoji} ", style=sma_range_color)
            display.append(f"${sma_range:.2f} ({sma_range_diff_pct:+.2f}%), ", style=sma_range_color)
            display.append(trend_range_direction, style=trend_range_color)
        else:
            display.append(f"SMA({self.current_range}): N/A", style="white")

        display.append("\n")

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
