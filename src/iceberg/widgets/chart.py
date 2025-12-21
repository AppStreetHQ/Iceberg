"""Chart widget using asciichartpy"""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static
from textual.containers import Vertical
from typing import Optional
import asciichartpy as acp

from ..data.db import Database


class ChartPanel(Widget):
    """Chart display with absolute/relative modes"""

    def __init__(self, db: Database, height: int = 15, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = db
        self.chart_height = height
        self.current_ticker: Optional[str] = None
        self.current_range: int = 30
        self.chart_mode: str = "absolute"  # "absolute" or "relative"

    def compose(self) -> ComposeResult:
        """Compose chart display"""
        with Vertical(id="chart_container"):
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
            self.query_one("#chart_display", Static).update(
                f"Insufficient data for {self.current_ticker}"
            )
            self.query_one("#chart_stats", Static).update("")
            return

        closes = [p.close for p in prices]

        # Render chart based on mode
        if self.chart_mode == "absolute":
            chart_str = self.render_absolute_chart(closes)
            mode_label = "Absolute Price"
        else:
            chart_str = self.render_relative_chart(closes)
            mode_label = "Relative % Change"

        # Calculate stats
        start_price = closes[0]
        end_price = closes[-1]
        high_price = max(closes)
        low_price = min(closes)
        change = end_price - start_price
        change_pct = (change / start_price) * 100 if start_price != 0 else 0

        stats = (
            f"{self.current_ticker} - {mode_label} ({self.current_range}d) | "
            f"Start: ${start_price:.2f} | High: ${high_price:.2f} | "
            f"Low: ${low_price:.2f} | Last: ${end_price:.2f} | "
            f"Change: {change:+.2f} ({change_pct:+.2f}%)"
        )

        # Update display
        self.query_one("#chart_display", Static).update(chart_str)
        self.query_one("#chart_stats", Static).update(stats)

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
