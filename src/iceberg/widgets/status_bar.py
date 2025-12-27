"""Status bar widget for bottom of screen"""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static
from rich.text import Text
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
        with Horizontal(id="status_container"):
            yield Static("", id="status_left")
            yield Static("", id="status_right")

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

    def update_status(self, message: str = "", color: Optional[str] = None) -> None:
        """Update status bar content

        Args:
            message: Status message to display
            color: Optional color for the message ('blue', 'red', 'green', etc.)
        """
        hints = "j/k:nav  c:chart  r:range  s:sort  d:day/range  e:copy  u:update  q:quit"
        market_info = f"Market: {self.market_status} {self.market_indicator}"

        # Build left side text
        left_text = Text()
        left_text.append(market_info, style="white")
        left_text.append(" | ", style="white")

        if message:
            if color:
                left_text.append(message, style=color)
            else:
                left_text.append(message, style="white")
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            left_text.append(f"Last update: {now}", style="white")

        left_text.append(" | ", style="white")
        left_text.append(hints, style="white")

        # Build right side text
        right_text = Text()
        right_text.append("Iceberg v1.0", style="white")

        status_left = self.query_one("#status_left", Static)
        status_right = self.query_one("#status_right", Static)
        status_left.update(left_text)
        status_right.update(right_text)

    def refresh_market_status(self) -> None:
        """Refresh market status and update display"""
        self.fetch_market_status()
        self.update_status()
