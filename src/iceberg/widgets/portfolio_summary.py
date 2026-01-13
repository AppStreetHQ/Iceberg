"""Portfolio summary panel showing total value and daily change"""

from textual.widget import Widget
from textual.widgets import Static
from textual.containers import Container
from textual.app import ComposeResult
from ..data.db import Database


class PortfolioSummary(Widget):
    """Portfolio summary panel showing total value and daily change"""

    def __init__(self, db: Database, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = db
        self.total_value_usd = 0.0
        self.total_value_gbp = 0.0
        self.daily_change_pct = 0.0
        self.daily_change_value = 0.0

    def compose(self) -> ComposeResult:
        """Compose the panel"""
        with Container(id="portfolio_container"):
            yield Static("PORTFOLIO", id="portfolio_header")
            yield Static("USD: --", id="portfolio_value_usd")
            yield Static("GBP: --", id="portfolio_value_gbp")
            yield Static("Today: --", id="portfolio_change")

    def on_mount(self) -> None:
        """Calculate portfolio on mount"""
        self.calculate_portfolio()

    def _convert_to_usd(self, amount: float, currency: str) -> float:
        """Convert amount to USD based on currency

        Args:
            amount: Amount in the source currency
            currency: Currency code (e.g., 'USD', 'GBP', 'EUR')

        Returns:
            Amount converted to USD
        """
        # Exchange rates to USD (approximate - could be made configurable)
        rates = {
            'USD': 1.0,
            'GBP': 1.27,  # GBP to USD
            'EUR': 1.10,  # EUR to USD
        }

        rate = rates.get(currency, 1.0)
        return amount * rate

    def _convert_to_gbp(self, amount: float, currency: str) -> float:
        """Convert amount to GBP based on currency

        Args:
            amount: Amount in the source currency
            currency: Currency code (e.g., 'USD', 'GBP', 'EUR')

        Returns:
            Amount converted to GBP
        """
        # Exchange rates to GBP (approximate - could be made configurable)
        rates = {
            'USD': 1.0 / 1.27,  # USD to GBP (~0.787)
            'GBP': 1.0,
            'EUR': 1.10 / 1.27,  # EUR to GBP via USD
        }

        rate = rates.get(currency, 1.0)
        return amount * rate

    def calculate_portfolio(self) -> None:
        """Calculate portfolio value and daily change (converted to both USD and GBP)"""
        holdings = self.db.get_all_holdings()

        total_current_usd = 0.0
        total_previous_usd = 0.0
        total_current_gbp = 0.0
        total_previous_gbp = 0.0

        for holding in holdings:
            # Get current and previous close prices
            current_price = self.db.get_latest_price(holding.ticker)
            previous_close_price = self.db.get_previous_close(holding.ticker)

            if current_price and previous_close_price:
                # Calculate value in native currency
                current_value = holding.shares * current_price.close
                previous_value = holding.shares * previous_close_price

                # Convert to USD
                current_value_usd = self._convert_to_usd(current_value, current_price.currency)
                previous_value_usd = self._convert_to_usd(previous_value, current_price.currency)

                # Convert to GBP
                current_value_gbp = self._convert_to_gbp(current_value, current_price.currency)
                previous_value_gbp = self._convert_to_gbp(previous_value, current_price.currency)

                total_current_usd += current_value_usd
                total_previous_usd += previous_value_usd
                total_current_gbp += current_value_gbp
                total_previous_gbp += previous_value_gbp

        self.total_value_usd = total_current_usd
        self.total_value_gbp = total_current_gbp

        # Calculate % change based on USD (use either, result should be same)
        if total_previous_usd > 0:
            self.daily_change_value = total_current_usd - total_previous_usd
            self.daily_change_pct = (self.daily_change_value / total_previous_usd) * 100
        else:
            self.daily_change_value = 0.0
            self.daily_change_pct = 0.0

        self.update_display()

    def update_display(self) -> None:
        """Update the display with current values"""
        usd_widget = self.query_one("#portfolio_value_usd", Static)
        gbp_widget = self.query_one("#portfolio_value_gbp", Static)
        change_widget = self.query_one("#portfolio_change", Static)

        # Format values
        usd_str = f"USD: ${self.total_value_usd:,.2f}"
        gbp_str = f"GBP: £{self.total_value_gbp:,.2f}"

        usd_widget.update(usd_str)
        gbp_widget.update(gbp_str)

        # Format change with color
        if self.daily_change_pct > 0:
            arrow = "▲"
            color = "green"
        elif self.daily_change_pct < 0:
            arrow = "▼"
            color = "red"
        else:
            arrow = "•"
            color = "white"

        change_str = f"Today: {arrow} ${abs(self.daily_change_value):,.2f} ({self.daily_change_pct:+.2f}%)"
        change_widget.update(f"[{color}]{change_str}[/{color}]")

    def refresh_portfolio(self) -> None:
        """Refresh portfolio calculations"""
        self.calculate_portfolio()
