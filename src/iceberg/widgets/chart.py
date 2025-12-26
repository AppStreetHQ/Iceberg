"""Chart widget using asciichartpy"""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static
from textual.containers import Vertical
from typing import Optional
import asciichartpy as acp
from rich.text import Text

from ..data.db import Database
from ..utils.formatting import COLOR_GAIN, COLOR_LOSS


class ChartPanel(Widget):
    """Chart display with absolute/relative modes"""

    def __init__(self, db: Database, height: int = 15, initial_day_range: int = 120, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = db
        self.chart_height = height
        self.current_ticker: Optional[str] = None
        self.current_range: int = initial_day_range  # Set from app
        self.chart_mode: str = "absolute"  # "absolute" or "relative"

    def compose(self) -> ComposeResult:
        """Compose chart display"""
        with Vertical(id="chart_container"):
            yield Static("", id="chart_header")
            yield Static("Select a ticker to view chart", id="chart_display")
            yield Static("", id="chart_stats")

    def update_ticker(self, ticker: str, day_range: Optional[int] = None) -> None:
        """Update chart for new ticker"""
        self.current_ticker = ticker
        if day_range is not None:
            self.current_range = day_range
        self.render_chart()

    def update_range(self, day_range: int) -> None:
        """Update day range"""
        self.current_range = day_range
        if self.current_ticker:
            self.render_chart()

    def toggle_mode(self) -> None:
        """Toggle between absolute and relative chart modes"""
        self.chart_mode = "relative" if self.chart_mode == "absolute" else "absolute"
        if self.current_ticker:
            self.render_chart()

    def render_chart(self) -> None:
        """Render the chart for current ticker and settings"""
        if not self.current_ticker:
            return

        # Fetch price data
        prices = self.db.get_daily_prices(self.current_ticker, self.current_range)

        if not prices or len(prices) < 2:
            self.query_one("#chart_header", Static).update("")
            self.query_one("#chart_display", Static).update(
                f"Insufficient data for {self.current_ticker}"
            )
            self.query_one("#chart_stats", Static).update("")
            return

        closes = [p.close for p in prices]

        # Calculate stats
        start_price = closes[0]
        end_price = closes[-1]
        high_price = max(closes)
        low_price = min(closes)
        change = end_price - start_price
        change_pct = (change / start_price) * 100 if start_price != 0 else 0

        # Determine color based on gain/loss
        is_gain = end_price >= start_price
        color = COLOR_GAIN if is_gain else COLOR_LOSS
        arrow = "▲" if is_gain else "▼"

        # Render chart based on mode with color indicator
        if self.chart_mode == "absolute":
            chart_str = self.render_absolute_chart(closes)
            mode_label = "Absolute Price"

            # Color Y-axis labels based on start price
            chart_display = self.color_yaxis_by_baseline(chart_str, start_price)
        else:
            chart_str = self.render_relative_chart(closes)
            mode_label = "Relative % Change"

            # Color Y-axis labels based on 0% baseline for relative mode
            chart_display = self.color_yaxis_by_baseline_percent(chart_str, 0.0)

        # Build header (above chart)
        header_text = Text()
        header_text.append(
            f"{self.current_ticker} - {mode_label} ({self.current_range}d)",
            style="bold bright_white"
        )

        # Build stats (below chart)
        stats_text = Text()
        stats_text.append(f"{arrow} ", style=color)
        stats_text.append(
            f"Start: ${start_price:.2f} | High: ${high_price:.2f} | "
            f"Low: ${low_price:.2f} | Last: ${end_price:.2f} | ",
            style="white"
        )
        stats_text.append(f"Change: {change:+.2f} ({change_pct:+.2f}%)", style=color)

        # Update display
        self.query_one("#chart_header", Static).update(header_text)
        self.query_one("#chart_display", Static).update(chart_display)
        self.query_one("#chart_stats", Static).update(stats_text)

    def render_absolute_chart(self, closes: list[float]) -> str:
        """Render absolute price chart"""
        try:
            config = {
                "height": self.chart_height,
                "format": "{:8.2f}",
            }
            return acp.plot(closes, config)
        except Exception as e:
            return f"Error rendering chart: {e}"

    def render_relative_chart(self, closes: list[float]) -> str:
        """Render relative % change chart"""
        if not closes or closes[0] == 0:
            return "No data"

        try:
            # Normalize to % change from first price
            start_price = closes[0]
            relative_pcts = [
                ((price - start_price) / start_price) * 100 for price in closes
            ]

            config = {
                "height": self.chart_height,
                "format": "{:6.2f}%",
            }
            return acp.plot(relative_pcts, config)
        except Exception as e:
            return f"Error rendering chart: {e}"

    def color_yaxis_by_baseline(self, chart_str: str, baseline_price: float) -> Text:
        """Color Y-axis labels green if >= baseline, red if < baseline"""
        result = Text()
        lines = chart_str.split("\n")

        for line in lines:
            if "┤" in line:
                # Split Y-axis label from chart
                parts = line.split("┤", 1)
                y_label = parts[0]
                chart_part = "┤" + parts[1] if len(parts) > 1 else ""

                # Try to extract price from Y-axis label
                try:
                    # Remove whitespace and extract number
                    price_str = y_label.strip()
                    price = float(price_str)

                    # Color based on baseline
                    if price >= baseline_price:
                        result.append(y_label, style=COLOR_GAIN)
                    else:
                        result.append(y_label, style=COLOR_LOSS)
                except (ValueError, AttributeError):
                    # If can't parse price, use default color
                    result.append(y_label, style="white")

                # Add chart part in white
                result.append(chart_part, style="white")
            else:
                # No Y-axis on this line, just append as is
                result.append(line, style="white")

            result.append("\n")

        return result

    def color_yaxis_by_baseline_percent(self, chart_str: str, baseline_pct: float) -> Text:
        """Color Y-axis percent labels green if >= baseline, red if < baseline"""
        result = Text()
        lines = chart_str.split("\n")

        for line in lines:
            if "┤" in line:
                # Split Y-axis label from chart
                parts = line.split("┤", 1)
                y_label = parts[0]
                chart_part = "┤" + parts[1] if len(parts) > 1 else ""

                # Extract percentage from Y-axis label
                # Format from asciichartpy is like "  8.32%" or " -1.00%"
                pct_str = y_label.strip().replace("%", "").strip()

                if pct_str:  # Only process non-empty labels
                    try:
                        # Remove any non-numeric chars except minus and decimal
                        pct_str_clean = ''.join(c for c in pct_str if c.isdigit() or c in '.-')
                        pct = float(pct_str_clean)

                        # Color based on baseline (0%)
                        if pct >= baseline_pct:
                            result.append(y_label, style=COLOR_GAIN)
                        else:
                            result.append(y_label, style=COLOR_LOSS)
                    except (ValueError, AttributeError):
                        # If parsing somehow fails, keep white
                        result.append(y_label, style="white")
                else:
                    # Empty label, keep white
                    result.append(y_label, style="white")

                # Add chart part in white
                result.append(chart_part, style="white")
            else:
                # No Y-axis on this line, just append as is
                result.append(line, style="white")

            result.append("\n")

        return result
