"""ASCII art ticker banner widget"""

from textual.widget import Widget
from textual.widgets import Static
from textual.app import ComposeResult
import pyfiglet

from ..data.db import Database


class TickerBanner(Widget):
    """Large ASCII art display of current ticker symbol"""

    def __init__(self, db: Database, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = db
        self.current_ticker = "AAPL"
        self.day_range = 90

    def compose(self) -> ComposeResult:
        """Compose the banner display"""
        yield Static("", id="ticker_ascii")
        yield Static("", id="company_name")
        yield Static("", id="date_range")

    def on_mount(self) -> None:
        """Render initial ticker on mount"""
        self.update_ticker(self.current_ticker, "Apple Inc.")

    def update_ticker(self, ticker: str, company_name: str = "") -> None:
        """Update the ASCII art for new ticker and company name"""
        self.current_ticker = ticker.upper()

        # Generate ASCII art using doom font
        try:
            ascii_art = pyfiglet.figlet_format(self.current_ticker, font="doom")
            # Strip trailing whitespace to reduce vertical space
            ascii_art = ascii_art.rstrip()
            self.query_one("#ticker_ascii", Static).update(ascii_art)
        except Exception as e:
            # Fallback to plain text if something goes wrong
            self.query_one("#ticker_ascii", Static).update(f"\n  {self.current_ticker}\n")

        # Update company name
        self.query_one("#company_name", Static).update(company_name)

        # Update date range
        self.update_date_range()

    def update_range(self, day_range: int) -> None:
        """Update day range and refresh date display"""
        self.day_range = day_range
        self.update_date_range()

    def update_date_range(self) -> None:
        """Update the date range display"""
        # Fetch prices for current ticker and range
        prices = self.db.get_daily_prices(self.current_ticker, self.day_range)

        if prices and len(prices) >= 2:
            start_date = prices[0].trade_date
            end_date = prices[-1].trade_date
            date_str = f"{self.day_range}d: {start_date.strftime('%d/%m/%y')} to {end_date.strftime('%d/%m/%y')}"
        else:
            date_str = f"{self.day_range}d: No data"

        self.query_one("#date_range", Static).update(date_str)
