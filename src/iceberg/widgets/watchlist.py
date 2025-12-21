"""Watchlist widget with ticker selection"""

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import OptionList
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

    def compose(self) -> ComposeResult:
        """Compose watchlist"""
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

            # Fetch latest and previous prices
            latest = self.db.get_latest_price(ticker)
            if latest:
                item.current_price = latest.close

            prev_close = self.db.get_previous_close(ticker)
            if prev_close:
                item.previous_close = prev_close

            self.items.append(item)

        # Populate option list
        self.update_display()

    def update_display(self) -> None:
        """Update the display with current data"""
        option_list = self.query_one("#ticker_list", OptionList)
        option_list.clear_options()

        for item in self.items:
            # Format display string
            price_str = format_price(item.current_price)
            change_str = format_change(item.price_change)
            change_pct_str = format_change_pct(item.price_change_pct)
            arrow = get_arrow(item.price_change)

            # Create Rich Text with color styling
            if item.current_price is not None and item.previous_close is not None:
                # Determine color based on gain/loss
                if item.is_gain:
                    color = COLOR_GAIN
                elif item.is_loss:
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
