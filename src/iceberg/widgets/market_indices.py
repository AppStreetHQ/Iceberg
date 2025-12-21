"""Market indices widget for top banner"""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static
from typing import Optional

from ..data.db import Database
from ..utils.formatting import format_price, format_change_pct, get_arrow


class MarketIndices(Widget):
    """Top banner showing major market indices"""

    def __init__(self, db: Database, indices: list[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = db
        self.indices = indices

    def compose(self) -> ComposeResult:
        """Compose indices display"""
        with Horizontal(id="indices_container"):
            for ticker in self.indices:
                yield Static("Loading...", id=f"index_{ticker}", classes="index_cell")

    def on_mount(self) -> None:
        """Load index data on mount"""
        self.update_indices()

    def update_indices(self) -> None:
        """Update all index displays"""
        for ticker in self.indices:
            self.update_index(ticker)

    def update_index(self, ticker: str) -> None:
        """Update single index display"""
        latest = self.db.get_latest_price(ticker)
        prev_close = self.db.get_previous_close(ticker)

        if not latest:
            content = f"{ticker}: N/A"
        else:
            price = latest.close
            change_pct = None

            if prev_close and prev_close != 0:
                change = price - prev_close
                change_pct = (change / prev_close) * 100
                arrow = get_arrow(change)
                change_str = format_change_pct(change_pct)

                # Determine color class
                color_class = "gain" if change > 0 else "loss" if change < 0 else "neutral"

                content = f"{ticker} {format_price(price)} {arrow} {change_str}"
                cell = self.query_one(f"#index_{ticker}", Static)
                cell.remove_class("gain", "loss", "neutral")
                cell.add_class(color_class)
            else:
                content = f"{ticker} {format_price(price)}"

        self.query_one(f"#index_{ticker}", Static).update(content)
