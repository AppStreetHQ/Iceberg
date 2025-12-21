"""ASCII art ticker banner widget"""

from textual.widget import Widget
from textual.widgets import Static
from textual.app import ComposeResult
import pyfiglet


class TickerBanner(Widget):
    """Large ASCII art display of current ticker symbol"""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.current_ticker = "AAPL"

    def compose(self) -> ComposeResult:
        """Compose the banner display"""
        yield Static("", id="ticker_ascii")
        yield Static("", id="company_name")

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
