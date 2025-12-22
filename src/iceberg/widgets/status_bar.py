"""Status bar widget for bottom of screen"""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..api.finnhub import FinnhubClient


class StatusBar(Widget):
    """Status bar showing hints and last update time"""

    def __init__(self, finnhub_client: Optional["FinnhubClient"] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.finnhub = finnhub_client
        self.market_status = "Unknown"
        self.market_indicator = "⚪"

    def compose(self) -> ComposeResult:
        """Compose status bar content"""
        yield Static("", id="status_content")

    def on_mount(self) -> None:
        """Initialize status bar"""
        self.fetch_market_status()
        self.update_status()

    def fetch_market_status(self) -> None:
        """Fetch market status from Finnhub API"""
        if not self.finnhub:
            return

        status = self.finnhub.get_market_status('US')
        if status:
            is_open = status.get('isOpen', False)
            session = status.get('session', 'unknown')

            if is_open:
                if session == 'pre':
                    self.market_status = "PRE-MARKET"
                    self.market_indicator = "🟡"
                elif session == 'post':
                    self.market_status = "AFTER-HOURS"
                    self.market_indicator = "🟡"
                else:
                    self.market_status = "OPEN"
                    self.market_indicator = "🟢"
            else:
                self.market_status = "CLOSED"
                self.market_indicator = "🔴"

    def update_status(self, message: str = "") -> None:
        """Update status bar content"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hints = "j/k:nav  c:chart  r:range  s:sort  d:day/range  u:update  q:quit"

        market_info = f"Market: {self.market_status} {self.market_indicator}"

        if message:
            content = f"{market_info} | {message} | {hints}"
        else:
            content = f"{market_info} | Last update: {now} | {hints}"

        status_widget = self.query_one("#status_content", Static)
        status_widget.update(content)

    def refresh_market_status(self) -> None:
        """Refresh market status and update display"""
        self.fetch_market_status()
        self.update_status()
