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
from pathlib import Path


class Watchlist(Widget):
    """Watchlist panel with ticker selection"""

    class TickerSelected(Message):
        """Message posted when a ticker is selected"""

        def __init__(self, ticker: str) -> None:
            self.ticker = ticker
            super().__init__()

    def __init__(self, db: Database, csv_path: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = db
        self.csv_path = csv_path
        self.items: list[WatchlistItem] = []
        self.sort_mode: str = "alpha"  # "alpha" or "change"
        self.change_mode: str = "day"  # "day" or "range"
        self.day_range: int = 90  # Current day range for range-based calculations

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

        # Sort and populate option list
        self.sort_items()
        self.update_display()

    def update_header(self) -> None:
        """Update the header label based on change mode"""
        if self.change_mode == "day":
            header_text = "Last Change"
        else:
            header_text = f"{self.day_range}d Range Change"

        self.query_one("#watchlist_header", Static).update(header_text)

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
                text.append(f"{item.ticker:<6} ", style="bold")
                text.append(f"{price_str:>10} {arrow} {change_str:>8} ({change_pct_str:>7})", style=color)

                display = text
            else:
                display = f"{item.ticker:<6} {price_str:>10}"

            option_list.add_option(Option(display, id=item.ticker))

        # Select first item by default
        if self.items:
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
        """Toggle sort mode and re-sort"""
        self.sort_mode = "change" if self.sort_mode == "alpha" else "alpha"
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

    def update_range(self, day_range: int) -> None:
        """Update day range and recalculate range-based changes"""
        self.day_range = day_range
        self.calculate_range_changes()
        if self.change_mode == "range":
            # Re-sort and update if we're in range mode
            self.sort_items()
            self.update_display()

    def toggle_change_mode(self) -> str:
        """Toggle between day and range change modes"""
        self.change_mode = "range" if self.change_mode == "day" else "day"
        # Re-sort and update display with new change mode
        self.sort_items()
        self.update_display()
        return self.change_mode

    def refresh_prices(self) -> None:
        """Refresh prices from database (after API update)"""
        # Remember currently selected ticker before re-sorting
        selected_ticker = self.get_selected_ticker()

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

        # Re-sort and update display
        self.sort_items()
        self.update_display()

        # Restore selection to the same ticker (which may have moved)
        if selected_ticker:
            option_list = self.query_one("#ticker_list", OptionList)
            for idx, item in enumerate(self.items):
                if item.ticker == selected_ticker:
                    option_list.highlighted = idx
                    break
