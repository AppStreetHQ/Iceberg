"""Modal dialog for entering portfolio holdings"""

from typing import Optional
from textual.screen import ModalScreen
from textual.widgets import Input, Static, Button
from textual.containers import Container, Horizontal
from textual.app import ComposeResult


class HoldingsInputDialog(ModalScreen[Optional[float]]):
    """Modal dialog for entering share holdings"""

    def __init__(self, ticker: str, current_shares: float = 0) -> None:
        super().__init__()
        self.ticker = ticker
        self.current_shares = current_shares

    def compose(self) -> ComposeResult:
        """Compose the dialog"""
        with Container(id="holdings_dialog"):
            yield Static(f"Enter Holdings for {self.ticker}", id="dialog_title")
            yield Static(
                f"Current: {self.current_shares:.2f} shares", id="current_holdings"
            )
            yield Input(
                value=str(self.current_shares) if self.current_shares > 0 else "",
                placeholder="Number of shares (0 to clear)",
                type="number",
                id="shares_input",
            )
            with Horizontal(id="dialog_buttons"):
                yield Button("Save", variant="primary", id="save_button")
                yield Button("Cancel", variant="default", id="cancel_button")

    def on_mount(self) -> None:
        """Focus the input when dialog appears"""
        self.query_one(Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks"""
        if event.button.id == "save_button":
            input_widget = self.query_one(Input)
            try:
                value = float(input_widget.value) if input_widget.value else 0.0
                self.dismiss(value)
            except ValueError:
                self.dismiss(None)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key"""
        try:
            value = float(event.value) if event.value else 0.0
            self.dismiss(value)
        except ValueError:
            self.dismiss(None)
