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
    compute_beta,
    find_support_resistance,
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

    def __init__(self, db: Database, initial_day_range: int = 120, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = db
        self.current_ticker: Optional[str] = None
        self.current_range: int = initial_day_range  # Set from app
        self.last_analysis_text: Optional[str] = None

    @staticmethod
    def format_volume(volume: float) -> str:
        """Format volume with K/M/B suffixes"""
        if volume >= 1_000_000_000:
            return f"{volume / 1_000_000_000:.1f}B"
        elif volume >= 1_000_000:
            return f"{volume / 1_000_000:.1f}M"
        elif volume >= 1_000:
            return f"{volume / 1_000:.1f}K"
        else:
            return f"{volume:.0f}"

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

        # Fetch price data - always use 365 days for consistent indicator calculation
        # MACD, RSI, SMAs should be calculated the same way regardless of selected range
        data_days = 365
        daily_prices = self.db.get_daily_prices(self.current_ticker, data_days)

        if not daily_prices or len(daily_prices) < 20:
            self.query_one("#technical_display", Static).update(
                f"Insufficient data for {self.current_ticker} technical analysis"
            )
            return

        # Extract closes and volumes
        closes = [p.close for p in daily_prices]
        volumes = [p.volume for p in daily_prices]

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

        # Beta (12mo) - calculate vs both SPY (market) and QQQ (tech)
        stock_daily = self.db.get_daily_prices(self.current_ticker, data_days)
        spy_daily = self.db.get_daily_prices("SPY", data_days)
        qqq_daily = self.db.get_daily_prices("QQQ", data_days)

        # Beta vs SPY (broad market)
        if stock_daily and spy_daily:
            stock_map = {dp.trade_date: dp.close for dp in stock_daily}
            spy_map = {dp.trade_date: dp.close for dp in spy_daily}
            common_dates_spy = sorted(set(stock_map.keys()) & set(spy_map.keys()))
            aligned_stock_closes_spy = [stock_map[d] for d in common_dates_spy]
            aligned_spy_closes = [spy_map[d] for d in common_dates_spy]
            beta_spy = compute_beta(aligned_stock_closes_spy, aligned_spy_closes)
        else:
            beta_spy = None

        # Beta vs QQQ (tech sector)
        if stock_daily and qqq_daily:
            stock_map = {dp.trade_date: dp.close for dp in stock_daily}
            qqq_map = {dp.trade_date: dp.close for dp in qqq_daily}
            common_dates_qqq = sorted(set(stock_map.keys()) & set(qqq_map.keys()))
            aligned_stock_closes_qqq = [stock_map[d] for d in common_dates_qqq]
            aligned_qqq_closes = [qqq_map[d] for d in common_dates_qqq]
            beta_qqq = compute_beta(aligned_stock_closes_qqq, aligned_qqq_closes)
        else:
            beta_qqq = None

        # v1.1 indicators
        distance_from_high = compute_distance_from_high(closes, 20)
        resilience_count = count_recovery_patterns(closes, 180)

        # Volume statistics (1 year or available)
        # Filter out zero volumes (incomplete/live trading days)
        valid_volumes = [v for v in volumes if v > 0]
        if valid_volumes:
            avg_volume = sum(valid_volumes) / len(valid_volumes)
            latest_volume = valid_volumes[-1]  # Most recent non-zero volume
            min_volume = min(valid_volumes)
            max_volume = max(valid_volumes)
            vol_diff_pct = ((latest_volume - avg_volume) / avg_volume) * 100
            vol_arrow = "▲" if latest_volume > avg_volume else "▼"
            vol_color = "#00ff00" if latest_volume > avg_volume else "#ff0000"
        else:
            avg_volume = latest_volume = min_volume = max_volume = 0
            vol_diff_pct = 0
            vol_arrow = "→"
            vol_color = "white"

        # Support/Resistance levels
        support, resistance = find_support_resistance(closes, window=5)

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

        # Current price and change (moved to top)
        if len(closes) >= 2:
            current = closes[-1]
            yesterday = closes[-2]
            change = current - yesterday
            change_pct = (change / yesterday * 100) if yesterday != 0 else 0

            if change > 0:
                change_color = "#00ff00"
                arrow = "▲"
            elif change < 0:
                change_color = "#ff0000"
                arrow = "▼"
            else:
                change_color = "white"
                arrow = "→"

            display.append("Price:           ")
            display.append(f"${current:.2f}  ", style="white")
            display.append(f"{arrow} ${abs(change):.2f} ({change_pct:+.2f}%)", style=change_color)
            display.append("\n")

        # 52-week high/low (moved to top)
        if len(closes) >= 240:
            range_days = min(252, len(closes))
            week52_high = max(closes[-range_days:])
            week52_low = min(closes[-range_days:])
            current = closes[-1]

            dist_from_high = ((current - week52_high) / week52_high * 100) if week52_high != 0 else 0
            dist_from_low = ((current - week52_low) / week52_low * 100) if week52_low != 0 else 0

            high_color = "#ff0000" if dist_from_high < -10 else "#ffaa00" if dist_from_high < 0 else "#00ff00"
            low_color = "#00ff00" if dist_from_low > 10 else "#ffaa00"

            display.append("52-Week Range:   ")
            display.append(f"High: ${week52_high:.2f} ({dist_from_high:+.1f}%)  ", style=high_color)
            display.append(f"Low: ${week52_low:.2f} ({dist_from_low:+.1f}%)", style=low_color)
            display.append("\n")

        # Volume statistics (1 year or available)
        display.append("Volume:          ")
        display.append(
            f"Avg {self.format_volume(avg_volume)} | Last Close {self.format_volume(latest_volume)} ",
            style="white"
        )
        display.append(f"{vol_arrow} ", style=vol_color)
        display.append(f"({vol_diff_pct:+.0f}%)", style=vol_color)
        display.append(
            f" | Range: {self.format_volume(min_volume)} - {self.format_volume(max_volume)}",
            style="white"
        )
        display.append("\n")

        display.append("\n")  # Blank line separator

        # MACD
        if macd:
            color = "#00ff00" if macd.bias == MACDBias.BULL else "#ff0000" if macd.bias == MACDBias.BEAR else "white"
            display.append("MACD(12,26,9):   ")
            display.append(macd.bias.value.title(), style=color)
            display.append(f" (MACD {macd.macd:.2f}, Signal {macd.signal:.2f}, Hist {macd.hist:.2f})\n", style="white")
        else:
            display.append("MACD(12,26,9):   N/A\n")

        # RSI
        if rsi:
            color_map = {
                RSIBias.OVERBOUGHT: "#ff0000",
                RSIBias.STRONG: "#00ff00",
                RSIBias.NEUTRAL: "white",
                RSIBias.WEAK: "#ffaa00",
                RSIBias.OVERSOLD: "#0088ff",
            }
            color = color_map.get(rsi.bias, "white")
            display.append("RSI(14):         ")
            display.append(f"{rsi.value:.1f}", style=color)
            display.append(f" - {rsi.bias.value.title()}\n", style=color)
        else:
            display.append("RSI(14):         N/A\n")

        # SMAs - side by side to save space
        current_price = closes[-1] if closes else 0

        # SMA(20) data
        if sma20:
            sma20_diff_pct = ((current_price - sma20) / sma20) * 100 if sma20 != 0 else 0
            sma20_emoji = "🟢" if current_price > sma20 else "🔴"
            sma20_color = "#00ff00" if current_price > sma20 else "#ff0000"

            if trend20:
                trend20_direction = "Up" if trend20.bias == TrendBias.UP else "Down" if trend20.bias == TrendBias.DOWN else "Sideways"
                trend20_color = "#00ff00" if trend20.bias == TrendBias.UP else "#ff0000" if trend20.bias == TrendBias.DOWN else "white"
            else:
                trend20_direction = "N/A"
                trend20_color = "white"

        # SMA(range) data
        sma_range = compute_sma(closes, len(closes)) if closes and len(closes) >= 2 else None
        if sma_range:
            sma_range_diff_pct = ((current_price - sma_range) / sma_range) * 100 if sma_range != 0 else 0
            sma_range_emoji = "🟢" if current_price > sma_range else "🔴"
            sma_range_color = "#00ff00" if current_price > sma_range else "#ff0000"

            if trend_range:
                trend_range_direction = "Up" if trend_range.bias == TrendBias.UP else "Down" if trend_range.bias == TrendBias.DOWN else "Sideways"
                trend_range_color = "#00ff00" if trend_range.bias == TrendBias.UP else "#ff0000" if trend_range.bias == TrendBias.DOWN else "white"
            else:
                trend_range_direction = "N/A"
                trend_range_color = "white"

        # Display SMAs side by side
        if sma20:
            arrow20 = "▲" if current_price > sma20 else "▼" if current_price < sma20 else "→"
            display.append("SMA(20):         ")
            display.append(f"${sma20:.2f} ({arrow20} {sma20_diff_pct:+.2f}%)", style=sma20_color)
            display.append(" Trend: ", style="white")
            display.append(trend20_direction, style=trend20_color)
        else:
            display.append("SMA(20):         N/A")

        display.append("  │  ", style="white")

        if sma_range:
            arrow_range = "▲" if current_price > sma_range else "▼" if current_price < sma_range else "→"
            display.append(f"SMA({self.current_range}): ")
            display.append(f"${sma_range:.2f} ({arrow_range} {sma_range_diff_pct:+.2f}%)", style=sma_range_color)
            display.append(" Trend: ", style="white")
            display.append(trend_range_direction, style=trend_range_color)
        else:
            display.append(f"SMA({self.current_range}): N/A")

        display.append("\n")

        # Helper function for beta interpretation
        def format_beta(beta_value, benchmark):
            if beta_value is None:
                return ("Insufficient data", "white")

            if beta_value < 0:
                color = "#00ffff"  # Cyan
                label = "Moves opposite"
            elif beta_value < 0.8:
                color = "#00ff00"  # Green
                label = "Less volatile"
            elif beta_value < 1.2:
                color = "white"
                label = "Similar"
            elif beta_value < 1.5:
                color = "#ffaa00"  # Orange
                label = "More volatile"
            else:
                color = "#ff0000"  # Red
                label = "High volatility"

            return (f"{beta_value:.2f} - {label}", color)

        # Volatility metrics (aligned)
        if volatility:
            color_map = {
                VolatilityBias.CALM: "#00ff00",
                VolatilityBias.CHOPPY: "#ffaa00",
                VolatilityBias.WILD: "#ff0000",
            }
            color = color_map.get(volatility.bias, "white")
            display.append("Volatility:      ")
            display.append(volatility.bias.value.title(), style=color)
            display.append(f" (daily σ = {volatility.sigma:.2f}%)\n", style="white")
        else:
            display.append("Volatility:      N/A\n")

        # Beta (both QQQ and SPY on same line)
        beta_qqq_text, beta_qqq_color = format_beta(beta_qqq, "QQQ")
        beta_spy_text, beta_spy_color = format_beta(beta_spy, "SPY")

        display.append("Beta (12mo):     ")
        display.append("QQQ: ", style="white")
        display.append(beta_qqq_text, style=beta_qqq_color)
        display.append("  │  ", style="white")
        display.append("SPY: ", style="white")
        display.append(beta_spy_text, style=beta_spy_color)
        display.append("\n")

        # Support/Resistance levels
        display.append("S/R Levels:      ")
        if support:
            support_pct = ((support - current_price) / current_price) * 100
            support_color = "#ffaa00" if abs(support_pct) < 5 else "white"  # Orange if close
            display.append(f"Support: ${support:.2f} ", style="white")
            display.append(f"({support_pct:+.1f}%)", style=support_color)
        else:
            display.append("Support: N/A", style="white")

        display.append("  │  ", style="white")

        if resistance:
            resistance_pct = ((resistance - current_price) / current_price) * 100
            resistance_color = "#ffaa00" if resistance_pct < 5 else "white"  # Orange if close
            display.append(f"Resistance: ${resistance:.2f} ", style="white")
            display.append(f"({resistance_pct:+.1f}%)", style=resistance_color)
        else:
            display.append("Resistance: N/A", style="white")

        display.append("\n")

        # Store plain text for clipboard export
        self.last_analysis_text = display.plain

        # Update display with Text object
        self.query_one("#technical_display", Static).update(display)
