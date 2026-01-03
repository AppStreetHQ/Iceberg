"""Chart widget using asciichartpy"""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static
from textual.containers import VerticalScroll
from typing import Optional, List, Tuple
import asciichartpy as acp
from rich.text import Text

from ..data.db import Database
from ..data.models import DailyPrice
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
        self.comparison_ticker: Optional[str] = None  # Ticker marked for comparison

    def compose(self) -> ComposeResult:
        """Compose chart display"""
        with VerticalScroll(id="chart_container"):
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

    def update_comparison(self, ticker: Optional[str]) -> None:
        """Update comparison ticker (None to disable comparison)"""
        self.comparison_ticker = ticker
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

        # Show comparison only if:
        # 1. There's a comparison ticker marked
        # 2. It's different from the current ticker
        if self.comparison_ticker and self.comparison_ticker != self.current_ticker:
            self.render_comparison_chart()
            return

        # Single ticker mode
        # Either no comparison ticker, or we're viewing the marked ticker itself
        # Check if we're viewing the marked ticker (should be shown in blue)
        is_marked_ticker = (self.current_ticker == self.comparison_ticker)

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

        # Calculate price stats
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

        # If viewing the marked comparison ticker, color its line blue
        if is_marked_ticker:
            chart_display = self.color_single_line_blue(chart_display)

        # Build header (above chart)
        header_text = Text()
        header_text.append(
            f"{self.current_ticker} - {mode_label} ({self.current_range}d)",
            style="bold bright_white"
        )

        # Build stats (below chart)
        # Color high, low, and last based on comparison to start
        high_color = COLOR_GAIN if high_price >= start_price else COLOR_LOSS
        low_color = COLOR_GAIN if low_price >= start_price else COLOR_LOSS
        last_color = COLOR_GAIN if end_price >= start_price else COLOR_LOSS

        stats_text = Text()
        stats_text.append(f"{arrow} ", style=color)
        stats_text.append(f"Start: ${start_price:.2f} | ", style="white")
        stats_text.append(f"High: ${high_price:.2f}", style=high_color)
        stats_text.append(" | ", style="white")
        stats_text.append(f"Low: ${low_price:.2f}", style=low_color)
        stats_text.append(" | ", style="white")
        stats_text.append(f"Last: ${end_price:.2f}", style=last_color)
        stats_text.append(" | ", style="white")
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

    def render_comparison_chart(self) -> None:
        """Render chart comparing two tickers"""
        # Fetch data for both tickers
        prices1 = self.db.get_daily_prices(self.current_ticker, self.current_range)
        prices2 = self.db.get_daily_prices(self.comparison_ticker, self.current_range)

        if not prices1 or not prices2:
            self.query_one("#chart_header", Static).update("")
            self.query_one("#chart_display", Static).update(
                "Insufficient data for comparison"
            )
            self.query_one("#chart_stats", Static).update("")
            return

        # Align to common dates
        aligned1, aligned2 = self.align_price_series(prices1, prices2)

        if not aligned1:
            self.query_one("#chart_header", Static).update("")
            self.query_one("#chart_display", Static).update(
                "No overlapping dates for comparison"
            )
            self.query_one("#chart_stats", Static).update("")
            return

        closes1 = [p.close for p in aligned1]
        closes2 = [p.close for p in aligned2]

        # Render based on mode
        if self.chart_mode == "absolute":
            # Calculate Y-axis range for both series combined
            all_values = closes1 + closes2
            y_min = min(all_values)
            y_max = max(all_values)

            chart_str = self.render_absolute_comparison(closes1, closes2, y_min, y_max)
            comparison_only = self.render_absolute_single(closes2, y_min, y_max)
            mode_label = "Absolute Price"
            chart_display = self.color_yaxis_by_baseline(chart_str, closes1[0])
            # Color the comparison line in cyan
            chart_display = self.color_comparison_line(chart_display, comparison_only)
        else:
            # Normalize both series
            start1 = closes1[0]
            relative_pcts1 = [((p - start1) / start1) * 100 for p in closes1]
            start2 = closes2[0]
            relative_pcts2 = [((p - start2) / start2) * 100 for p in closes2]

            # Calculate Y-axis range for both series combined
            all_pcts = relative_pcts1 + relative_pcts2
            y_min = min(all_pcts)
            y_max = max(all_pcts)

            chart_str = self.render_relative_comparison(closes1, closes2, y_min, y_max)
            comparison_only = self.render_relative_single(relative_pcts2, y_min, y_max)
            mode_label = "Relative % Change"
            chart_display = self.color_yaxis_by_baseline_percent(chart_str, 0.0)
            # Color the comparison line in cyan
            chart_display = self.color_comparison_line(chart_display, comparison_only)

        # Update header
        header_text = Text()
        header_text.append(
            f"{self.current_ticker} vs {self.comparison_ticker} - {mode_label} ({self.current_range}d)",
            style="bold bright_white"
        )
        self.query_one("#chart_header", Static).update(header_text)

        # Update chart
        self.query_one("#chart_display", Static).update(chart_display)

        # Update stats (both tickers)
        self.update_comparison_stats(aligned1, aligned2, closes1, closes2)

    def render_absolute_comparison(self, closes1: list[float], closes2: list[float], y_min: float, y_max: float) -> str:
        """Render absolute price chart for two tickers with explicit Y-axis range"""
        try:
            config = {
                "height": self.chart_height,
                "format": "{:8.2f}",
                "min": y_min,
                "max": y_max,
            }
            return acp.plot([closes1, closes2], config)
        except Exception as e:
            return f"Error: {e}"

    def render_relative_comparison(self, closes1: list[float], closes2: list[float], y_min: float, y_max: float) -> str:
        """Render relative % change chart for two tickers with explicit Y-axis range"""
        if not closes1 or not closes2 or closes1[0] == 0 or closes2[0] == 0:
            return "No data"

        try:
            # Normalize both to % change from their own first price
            start1 = closes1[0]
            relative_pcts1 = [((p - start1) / start1) * 100 for p in closes1]

            start2 = closes2[0]
            relative_pcts2 = [((p - start2) / start2) * 100 for p in closes2]

            config = {
                "height": self.chart_height,
                "format": "{:6.2f}%",
                "min": y_min,
                "max": y_max,
            }
            return acp.plot([relative_pcts1, relative_pcts2], config)
        except Exception as e:
            return f"Error: {e}"

    def align_price_series(
        self,
        prices1: List[DailyPrice],
        prices2: List[DailyPrice]
    ) -> Tuple[List[DailyPrice], List[DailyPrice]]:
        """Align two price series by date, returning only common dates"""
        # Create date -> price mappings
        map1 = {p.trade_date: p for p in prices1}
        map2 = {p.trade_date: p for p in prices2}

        # Find common dates
        common_dates = sorted(set(map1.keys()) & set(map2.keys()))

        # Return aligned lists
        aligned1 = [map1[d] for d in common_dates]
        aligned2 = [map2[d] for d in common_dates]

        return aligned1, aligned2

    def update_comparison_stats(
        self,
        aligned1: List[DailyPrice],
        aligned2: List[DailyPrice],
        closes1: list[float],
        closes2: list[float]
    ) -> None:
        """Update stats section for comparison mode"""
        stats_text = Text()

        # Ticker 1 stats
        start1, end1 = closes1[0], closes1[-1]
        change1 = end1 - start1
        change_pct1 = (change1 / start1) * 100 if start1 else 0
        color1 = COLOR_GAIN if change1 >= 0 else COLOR_LOSS
        arrow1 = "▲" if change1 >= 0 else "▼"

        stats_text.append(f"{arrow1} ", style=color1)
        stats_text.append(f"{self.current_ticker}: ", style="bold white")
        stats_text.append(f"${start1:.2f} → ${end1:.2f} ", style="white")
        stats_text.append(f"{change1:+.2f} ({change_pct1:+.2f}%)", style=color1)
        stats_text.append("\n")

        # Ticker 2 stats
        start2, end2 = closes2[0], closes2[-1]
        change2 = end2 - start2
        change_pct2 = (change2 / start2) * 100 if start2 else 0
        color2 = COLOR_GAIN if change2 >= 0 else COLOR_LOSS
        arrow2 = "▲" if change2 >= 0 else "▼"

        stats_text.append(f"{arrow2} ", style=color2)
        stats_text.append(f"{self.comparison_ticker}: ", style="bold cyan")
        stats_text.append(f"${start2:.2f} → ${end2:.2f} ", style="white")
        stats_text.append(f"{change2:+.2f} ({change_pct2:+.2f}%)", style=color2)

        self.query_one("#chart_stats", Static).update(stats_text)

    def render_absolute_single(self, closes: list[float], y_min: float, y_max: float) -> str:
        """Render absolute price chart for single ticker with explicit Y-axis range"""
        try:
            config = {
                "height": self.chart_height,
                "format": "{:8.2f}",
                "min": y_min,
                "max": y_max,
            }
            return acp.plot(closes, config)
        except Exception:
            return ""

    def render_relative_single(self, relative_pcts: list[float], y_min: float, y_max: float) -> str:
        """Render relative % chart for single ticker with explicit Y-axis range"""
        try:
            config = {
                "height": self.chart_height,
                "format": "{:6.2f}%",
                "min": y_min,
                "max": y_max,
            }
            return acp.plot(relative_pcts, config)
        except Exception:
            return ""

    def color_comparison_line(self, chart_display: Text, comparison_only: str) -> Text:
        """Color the comparison ticker's line in cyan by comparing chart outputs"""
        if not comparison_only:
            return chart_display

        # Get the plain text from chart_display to work with
        display_str = chart_display.plain

        # Split both charts into lines
        display_lines = display_str.split("\n")
        comparison_lines = comparison_only.split("\n")

        # Build new colored output preserving y-axis colors
        result = Text()

        # Extract the spans (styled segments) from original chart_display
        # We'll preserve y-axis colors and add line colors
        line_start = 0
        for i, display_line in enumerate(display_lines):
            if i >= len(comparison_lines):
                # No comparison line for this row, keep original styling
                line_end = line_start + len(display_line)
                for span in chart_display._spans:
                    if span.start >= line_start and span.end <= line_end + 1:  # +1 for \n
                        start = span.start - line_start
                        end = span.end - line_start
                        if end > start:
                            result.append(display_line[start:end], style=span.style)
                result.append("\n")
                line_start = line_end + 1
                continue

            comp_line = comparison_lines[i]

            # Process character by character
            if "┤" in display_line:
                # Split at the axis separator
                parts = display_line.split("┤", 1)
                y_axis = parts[0]
                chart_part = parts[1] if len(parts) > 1 else ""

                # Find and preserve y-axis color from original
                y_axis_end = len(y_axis)
                y_axis_color = "white"
                for span in chart_display._spans:
                    span_start_in_line = span.start - line_start
                    if 0 <= span_start_in_line < y_axis_end:
                        y_axis_color = span.style
                        break

                result.append(y_axis, style=y_axis_color)
                result.append("┤", style="white")

                # Split comparison line similarly
                comp_parts = comp_line.split("┤", 1)
                comp_chart = comp_parts[1] if len(comp_parts) > 1 else ""

                # Color chart characters
                for j, char in enumerate(chart_part):
                    if j < len(comp_chart) and comp_chart[j] != ' ' and char == comp_chart[j]:
                        # This character belongs to comparison line - color it cyan
                        result.append(char, style="#00ffff")
                    else:
                        # This character belongs to current ticker or is empty - keep white
                        result.append(char, style="white")
            else:
                # No axis on this line, keep white
                result.append(display_line, style="white")

            result.append("\n")
            line_start += len(display_line) + 1  # +1 for \n

        return result

    def color_single_line_blue(self, chart_display: Text) -> Text:
        """Color the chart line blue for marked comparison ticker"""
        # Get the plain text from chart_display
        display_str = chart_display.plain
        display_lines = display_str.split("\n")

        # Build new output with blue chart lines
        result = Text()

        line_start = 0
        for i, display_line in enumerate(display_lines):
            if "┤" in display_line:
                # Split at the axis separator
                parts = display_line.split("┤", 1)
                y_axis = parts[0]
                chart_part = parts[1] if len(parts) > 1 else ""

                # Preserve y-axis color from original
                y_axis_end = len(y_axis)
                y_axis_color = "white"
                for span in chart_display._spans:
                    span_start_in_line = span.start - line_start
                    if 0 <= span_start_in_line < y_axis_end:
                        y_axis_color = span.style
                        break

                result.append(y_axis, style=y_axis_color)
                result.append("┤", style="white")

                # Color chart part in blue
                result.append(chart_part, style="#00ffff")
            else:
                # No axis on this line
                result.append(display_line, style="white")

            result.append("\n")
            line_start += len(display_line) + 1  # +1 for \n

        return result
