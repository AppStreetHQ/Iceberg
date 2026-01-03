"""Watchlist widget with ticker selection"""

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option
from typing import Optional
from rich.text import Text

from ..data.db import Database
from ..data.loader import load_watchlist_from_csv
from ..data.models import WatchlistItem
from ..utils.formatting import (
    format_price,
    format_change,
    format_change_pct,
    get_arrow,
    COLOR_GAIN,
    COLOR_LOSS,
    COLOR_NEUTRAL,
)
from ..analysis.scoring import get_rating_color
from pathlib import Path


class Watchlist(Widget):
    """Watchlist panel with ticker selection"""

    class TickerSelected(Message):
        """Message posted when a ticker is selected"""

        def __init__(self, ticker: str) -> None:
            self.ticker = ticker
            super().__init__()

    def __init__(self, db: Database, csv_path: Path, initial_day_range: int = 120, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = db
        self.csv_path = csv_path
        self.items: list[WatchlistItem] = []
        self.sort_mode: str = "change"  # "alpha" or "change" - default to performance
        self.change_mode: str = "day"  # "day" or "range"
        self.day_range: int = initial_day_range  # Set from app
        self._preserved_ticker: Optional[str] = None  # Preserve selection across updates
        self.comparison_ticker: Optional[str] = None  # Ticker marked for comparison
        self.selected_ticker: Optional[str] = None  # Currently selected/viewed ticker

    def compose(self) -> ComposeResult:
        """Compose watchlist"""
        yield Static("", id="watchlist_header")
        yield OptionList(id="ticker_list")

    def on_mount(self) -> None:
        """Load watchlist on mount"""
        self.load_watchlist()

    def load_watchlist(self) -> None:
        """Load tickers from CSV and fetch prices"""
        # Load tickers from CSV
        ticker_pairs = load_watchlist_from_csv(self.csv_path)

        # Create watchlist items and fetch prices
        self.items = []
        for ticker, name in ticker_pairs:
            item = WatchlistItem(ticker=ticker, name=name)

            # Fetch latest and previous prices for daily change
            latest = self.db.get_latest_price(ticker)
            if latest:
                item.current_price = latest.close

            prev_close = self.db.get_previous_close(ticker)
            if prev_close:
                item.previous_close = prev_close

            self.items.append(item)

        # Calculate range-based changes
        self.calculate_range_changes()

        # Calculate Iceberg scores
        self.calculate_scores()

        # Sort and populate option list
        self.sort_items()
        self.update_display()

    def update_header(self) -> None:
        """Update the header label based on change mode and sort mode"""
        if self.change_mode == "day":
            change_text = "Last Change"
        else:
            change_text = f"{self.day_range}d Range Change"

        # Add sort mode indicator
        sort_label = {
            "alpha": "Alpha",
            "trade": "Trade Score",
            "investment": "Investment Score",
            "change": "Change"
        }.get(self.sort_mode, "Unknown")

        # Use Rich Text with bold only for "Watchlist"
        header = Text()
        header.append("Watchlist", style="bold")
        header.append(f" | {change_text}\nSort: {sort_label}")

        self.query_one("#watchlist_header", Static).update(header)

    def update_display(self) -> None:
        """Update the display with current data"""
        self.update_header()
        option_list = self.query_one("#ticker_list", OptionList)
        option_list.clear_options()

        for item in self.items:
            # Use range or day change based on change_mode
            if self.change_mode == "range":
                change = item.range_change
                change_pct = item.range_change_pct
            else:
                change = item.price_change
                change_pct = item.price_change_pct

            # Format display string
            price_str = format_price(item.current_price)
            change_str = format_change(change)
            change_pct_str = format_change_pct(change_pct)
            arrow = get_arrow(change)

            # Create Rich Text with color styling
            if item.current_price is not None and change is not None:
                # Determine color based on gain/loss
                if change > 0:
                    color = COLOR_GAIN
                elif change < 0:
                    color = COLOR_LOSS
                else:
                    color = "white"

                # Build styled text
                text = Text()
                # Color comparison ticker in iceberg blue
                ticker_style = "bold #00ffff" if item.ticker == self.comparison_ticker else "bold"
                text.append(f"{item.ticker:<6} ", style=ticker_style)

                # Add colored T and I score indicators
                if item.trade_score is not None:
                    trade_color = get_rating_color(item.trade_score)
                    text.append("T", style=trade_color)
                else:
                    text.append("T", style="dim")

                if item.investment_score is not None:
                    inv_color = get_rating_color(item.investment_score)
                    text.append("I", style=inv_color)
                else:
                    text.append("I", style="dim")

                text.append(f" {price_str:>10} {arrow} {change_str:>8} ({change_pct_str:>7})", style=color)

                # Add asterisk for comparison ticker
                if item.ticker == self.comparison_ticker:
                    text.append(" *", style="bold cyan")

                display = text
            else:
                # Plain text display for items without price data
                text = Text()
                # Color comparison ticker in iceberg blue
                ticker_style = "bold #00ffff" if item.ticker == self.comparison_ticker else "bold"
                text.append(f"{item.ticker:<6} ", style=ticker_style)
                text.append(f"TI {price_str:>10}")

                # Add asterisk for comparison ticker
                if item.ticker == self.comparison_ticker:
                    text.append(" *", style="bold cyan")

                display = text

            option_list.add_option(Option(display, id=item.ticker))

        # Restore preserved selection, or default to first item
        if self.items:
            restored = False
            if self._preserved_ticker:
                # Find and restore the preserved ticker
                for idx, item in enumerate(self.items):
                    if item.ticker == self._preserved_ticker:
                        option_list.highlighted = idx
                        restored = True
                        break

            # Default to first item if no preserved selection
            if not restored:
                option_list.highlighted = 0

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle ticker selection"""
        if event.option_id:
            self.post_message(self.TickerSelected(event.option_id))

    def get_selected_ticker(self) -> Optional[str]:
        """Get currently selected ticker"""
        option_list = self.query_one("#ticker_list", OptionList)
        if option_list.highlighted is not None and self.items:
            idx = option_list.highlighted
            if 0 <= idx < len(self.items):
                return self.items[idx].ticker
        return None

    def set_comparison_ticker(self, ticker: Optional[str]) -> None:
        """Set the comparison ticker and update display"""
        old_comparison = self.comparison_ticker
        self.comparison_ticker = ticker

        # Only rebuild if comparison ticker actually changed
        if old_comparison != ticker:
            self._preserved_ticker = self.get_selected_ticker()  # Preserve current selection
            self.update_display()

    def set_selected_ticker(self, ticker: Optional[str]) -> None:
        """Set the currently selected/viewed ticker and update display"""
        old_selected = self.selected_ticker
        self.selected_ticker = ticker

        # Only rebuild if selected ticker actually changed
        if old_selected != ticker:
            self._preserved_ticker = self.get_selected_ticker()  # Preserve current selection
            self.update_display()

    def get_selected_item(self) -> Optional[WatchlistItem]:
        """Get currently selected watchlist item"""
        option_list = self.query_one("#ticker_list", OptionList)
        if option_list.highlighted is not None and self.items:
            idx = option_list.highlighted
            if 0 <= idx < len(self.items):
                return self.items[idx]
        return None

    def sort_items(self) -> None:
        """Sort items based on current sort mode"""
        if self.sort_mode == "alpha":
            # Sort alphabetically by ticker
            self.items.sort(key=lambda x: x.ticker)
        elif self.sort_mode == "trade":
            # Sort by Trade Score (descending), then alphabetically
            self.items.sort(
                key=lambda x: (
                    -(x.trade_score if x.trade_score is not None else -999),
                    x.ticker
                )
            )
        elif self.sort_mode == "investment":
            # Sort by Investment Score (descending), then alphabetically
            self.items.sort(
                key=lambda x: (
                    -(x.investment_score if x.investment_score is not None else -999),
                    x.ticker
                )
            )
        elif self.sort_mode == "change":
            # Sort by price change % (descending, best performers first)
            # Use range or day change based on change_mode
            if self.change_mode == "range":
                self.items.sort(
                    key=lambda x: x.range_change_pct if x.range_change_pct is not None else -999999,
                    reverse=True
                )
            else:
                self.items.sort(
                    key=lambda x: x.price_change_pct if x.price_change_pct is not None else -999999,
                    reverse=True
                )

    def toggle_sort(self) -> str:
        """Cycle through sort modes: change → alpha → trade → investment → change"""
        # Preserve selection before sorting
        self._preserved_ticker = self.get_selected_ticker()

        if self.sort_mode == "change":
            self.sort_mode = "alpha"
        elif self.sort_mode == "alpha":
            self.sort_mode = "trade"
        elif self.sort_mode == "trade":
            self.sort_mode = "investment"
        else:  # investment
            self.sort_mode = "change"

        self.sort_items()
        self.update_display()
        return self.sort_mode

    def calculate_range_changes(self) -> None:
        """Calculate price changes over the selected day range"""
        for item in self.items:
            # Fetch prices for the range
            prices = self.db.get_daily_prices(item.ticker, self.day_range)

            if prices and len(prices) >= 2:
                start_price = prices[0].close
                end_price = prices[-1].close

                item.range_start_price = start_price
                item.range_change = end_price - start_price
                item.range_change_pct = (
                    ((end_price - start_price) / start_price) * 100
                    if start_price != 0 else None
                )
            else:
                item.range_start_price = None
                item.range_change = None
                item.range_change_pct = None

    def calculate_scores(self) -> None:
        """Calculate Iceberg scores for all watchlist items"""
        from ..analysis.scoring import calculate_trade_score, calculate_investment_score
        from ..analysis.indicators import (
            compute_macd,
            compute_rsi,
            compute_sma,
            compute_trend,
            compute_volatility,
            compute_distance_from_high,
            count_recovery_patterns,
            compute_long_term_trend,
            find_support_resistance,
        )

        for item in self.items:
            # Fetch closing prices for score calculation (365 days)
            closes = self.db.get_closing_prices(item.ticker, 365)

            if closes and len(closes) >= 20:
                # Calculate all indicators (same as technical panel)
                current_price = closes[-1]
                macd = compute_macd(closes)
                rsi = compute_rsi(closes, 14)
                sma10 = compute_sma(closes, 10)
                sma20 = compute_sma(closes, 20)
                sma50 = compute_sma(closes, 50)
                sma100 = compute_sma(closes, 100)
                trend10 = compute_trend(closes, 10)
                trend50 = compute_trend(closes, 50)
                long_term_trend = compute_long_term_trend(closes, 100)
                volatility = compute_volatility(closes)
                distance_from_high = compute_distance_from_high(closes, 20)
                resilience_count = count_recovery_patterns(closes, 180)
                support, resistance = find_support_resistance(closes, window=5)

                # Calculate both scores with all indicators
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
                    closes=closes,
                    support=support,
                    resistance=resistance
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

                item.trade_score = trade_result.display_score
                item.investment_score = inv_result.display_score
            else:
                # Insufficient data
                item.trade_score = None
                item.investment_score = None

    def update_range(self, day_range: int) -> None:
        """Update day range and recalculate range-based changes"""
        self.day_range = day_range
        self.calculate_range_changes()
        if self.change_mode == "range":
            # Preserve selection before re-sorting
            self._preserved_ticker = self.get_selected_ticker()
            # Re-sort and update if we're in range mode
            self.sort_items()
            self.update_display()

    def toggle_change_mode(self) -> str:
        """Toggle between day and range change modes"""
        # Preserve selection before sorting
        self._preserved_ticker = self.get_selected_ticker()

        self.change_mode = "range" if self.change_mode == "day" else "day"
        # Re-sort and update display with new change mode
        self.sort_items()
        self.update_display()
        return self.change_mode

    def refresh_prices(self) -> None:
        """Refresh prices from database (after API update)"""
        # Preserve currently selected ticker (update_display will restore it)
        self._preserved_ticker = self.get_selected_ticker()

        # Update prices for all items
        for item in self.items:
            # Fetch latest and previous prices for daily change
            latest = self.db.get_latest_price(item.ticker)
            if latest:
                item.current_price = latest.close

            prev_close = self.db.get_previous_close(item.ticker)
            if prev_close:
                item.previous_close = prev_close

        # Recalculate range-based changes
        self.calculate_range_changes()

        # Recalculate Iceberg scores
        self.calculate_scores()

        # Re-sort and update display (will restore selection automatically)
        self.sort_items()
        self.update_display()
