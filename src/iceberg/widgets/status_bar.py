"""Status bar widget for bottom of screen"""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static
from datetime import datetime


class StatusBar(Widget):
    """Status bar showing hints and last update time"""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        """Compose status bar content"""
        yield Static("", id="status_content")

    def on_mount(self) -> None:
        """Initialize status bar"""
        self.update_status()

    def update_status(self, message: str = "") -> None:
        """Update status bar content"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hints = "j/k:nav  c:chart  r:range  s:sort  d:day/range  q:quit"

        if message:
            content = f"{message} | {hints}"
        else:
            content = f"Last update: {now} | {hints}"

        status_widget = self.query_one("#status_content", Static)
        status_widget.update(content)
