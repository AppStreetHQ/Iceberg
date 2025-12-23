"""ASCII art ticker banner widget"""

from textual.widget import Widget
from textual.widgets import Static
from textual.app import ComposeResult
from typing import Optional
import pyfiglet

from ..data.db import Database
from ..utils.formatting import format_market_cap


class TickerBanner(Widget):
    """Large ASCII art display of current ticker symbol"""

    def __init__(self, db: Database, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = db
        self.current_ticker = "AAPL"

    def compose(self) -> ComposeResult:
        """Compose the banner display"""
        yield Static("", id="ticker_ascii")
        yield Static("", id="company_name")
        yield Static("", id="industry")
        yield Static("", id="market_cap")

    def on_mount(self) -> None:
        """Render initial ticker on mount"""
        # Will be updated by app after mount
        pass

    def update_ticker(
        self,
        ticker: str,
        company_name: str = "",
        industry: Optional[str] = None,
        shares_outstanding: Optional[float] = None,
        current_price: Optional[float] = None,
        currency: str = "USD"
    ) -> None:
        """Update ticker banner with company info and live market cap

        Args:
            ticker: Stock ticker symbol
            company_name: Company name
            industry: Industry classification
            shares_outstanding: Number of shares outstanding (in millions)
            current_price: Current stock price
            currency: Currency code for market cap display
        """
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

        # Update company name (strip leading/trailing whitespace)
        self.query_one("#company_name", Static).update(company_name.strip() if company_name else "")

        # Update industry
        industry_text = industry if industry else "N/A"
        self.query_one("#industry", Static).update(industry_text)

        # Calculate and update live market cap
        if shares_outstanding and current_price:
            # shares_outstanding is in millions, so multiply by 1M
            market_cap = shares_outstanding * 1_000_000 * current_price
            market_cap_text = f"Market cap: {format_market_cap(market_cap, currency)}"
        else:
            market_cap_text = "Market cap: N/A"

        self.query_one("#market_cap", Static).update(market_cap_text)
