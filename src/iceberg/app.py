"""Main Iceberg Terminal application"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Header
from textual.worker import Worker, WorkerState

from .config import Config
from .data.db import Database
from .api.finnhub import FinnhubClient
from .widgets.market_indices import MarketIndices
from .widgets.ticker_banner import TickerBanner
from .widgets.watchlist import Watchlist
from .widgets.chart import ChartPanel
from .widgets.technical_panel import TechnicalPanel
from .widgets.status_bar import StatusBar


class IcebergApp(App):
    """Iceberg Terminal - Bloomberg-style stock market TUI"""

    TITLE = "Iceberg Terminal"
    SUB_TITLE = "v1.0"

    CSS_PATH = "app.tcss"
    SHOW_FOOTER = False  # Disable built-in footer, we have custom StatusBar

    BINDINGS = [
        Binding("j", "watchlist_down", "Next ticker", show=False),
        Binding("k", "watchlist_up", "Previous ticker", show=False),
        Binding("down", "watchlist_down", "Next ticker", show=False),
        Binding("up", "watchlist_up", "Previous ticker", show=False),
        Binding("c", "toggle_chart_mode", "Toggle chart mode", show=True),
        Binding("r", "cycle_day_range", "Cycle day range", show=True),
        Binding("s", "toggle_sort", "Toggle sort", show=True),
        Binding("d", "toggle_change_mode", "Toggle day/range", show=True),
        Binding("e", "export_ta", "Copy TA", show=True),
        Binding("u", "update_prices", "Update prices", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    # Reactive state - automatically updates UI when changed
    selected_ticker = reactive("AAPL", init=False)
    day_range = reactive(120, init=False)  # 7, 30, 90, 120
    chart_mode = reactive("absolute", init=False)  # "absolute" or "relative"

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.db = Database(config.db_path)
        self.finnhub = FinnhubClient()
        self.day_ranges = [7, 30, 90, 120]
        self.day_range_index = 3  # Start at 120 days
        self.profile_cache = {}  # Cache company profiles by ticker

    def compose(self) -> ComposeResult:
        """Create child widgets"""
        yield Header(show_clock=True)
        yield MarketIndices(self.db, self.config.market_indices)

        with Horizontal(id="content"):
            with Vertical(id="left_panel"):
                yield TickerBanner(self.db, id="ticker_banner")
                yield Watchlist(self.db, self.config.watchlist_csv, self.day_range, id="watchlist")
            with Vertical(id="main_display"):
                yield ChartPanel(self.db, self.config.chart_height, self.day_range, id="chart")
                yield TechnicalPanel(self.db, self.day_range, id="technical")

        yield StatusBar(finnhub_client=self.finnhub, id="status_bar")

    def on_mount(self) -> None:
        """Initialize app on mount"""
        # Get first ticker from watchlist and select it
        watchlist = self.query_one("#watchlist", Watchlist)
        first_ticker = watchlist.get_selected_ticker()
        if first_ticker:
            self.selected_ticker = first_ticker
            self.update_panels()

        # Initialize banner with date range
        banner = self.query_one(MarketIndices)
        banner.update_range(self.day_range, self.selected_ticker)

    def on_watchlist_ticker_selected(self, message: Watchlist.TickerSelected) -> None:
        """Handle ticker selection from watchlist"""
        self.selected_ticker = message.ticker
        self.update_panels()

    def update_panels(self) -> None:
        """Update chart and technical panels with current ticker and range"""
        # Get company name and current price from watchlist
        watchlist = self.query_one("#watchlist", Watchlist)
        company_name = ""
        current_price = None
        for item in watchlist.items:
            if item.ticker == self.selected_ticker:
                company_name = item.name
                current_price = item.current_price
                break

        # Fetch profile data (cached per session)
        if self.selected_ticker not in self.profile_cache:
            profile = self.finnhub.get_company_profile(self.selected_ticker)
            self.profile_cache[self.selected_ticker] = profile
        else:
            profile = self.profile_cache[self.selected_ticker]

        # Extract profile data
        industry = None
        shares_outstanding = None
        currency = "USD"
        if profile:
            industry = profile.get('finnhubIndustry')
            shares_outstanding = profile.get('shareOutstanding')
            currency = profile.get('currency', 'USD')

        # Update ticker banner with profile info
        banner = self.query_one("#ticker_banner", TickerBanner)
        banner.update_ticker(
            self.selected_ticker,
            company_name,
            industry,
            shares_outstanding,
            current_price,
            currency
        )

        chart = self.query_one("#chart", ChartPanel)
        technical = self.query_one("#technical", TechnicalPanel)

        chart.update_ticker(self.selected_ticker, self.day_range)
        technical.update_ticker(self.selected_ticker, self.day_range)

    def action_watchlist_down(self) -> None:
        """Move down in watchlist"""
        watchlist = self.query_one("#watchlist", Watchlist)
        option_list = watchlist.query_one("#ticker_list")
        if option_list.highlighted is not None:
            max_idx = len(watchlist.items) - 1
            if option_list.highlighted < max_idx:
                option_list.highlighted += 1
                # Trigger selection
                ticker = watchlist.get_selected_ticker()
                if ticker:
                    self.selected_ticker = ticker
                    self.update_panels()

    def action_watchlist_up(self) -> None:
        """Move up in watchlist"""
        watchlist = self.query_one("#watchlist", Watchlist)
        option_list = watchlist.query_one("#ticker_list")
        if option_list.highlighted is not None and option_list.highlighted > 0:
            option_list.highlighted -= 1
            # Trigger selection
            ticker = watchlist.get_selected_ticker()
            if ticker:
                self.selected_ticker = ticker
                self.update_panels()

    def action_toggle_chart_mode(self) -> None:
        """Toggle between absolute and relative chart modes"""
        chart = self.query_one("#chart", ChartPanel)
        chart.toggle_mode()
        self.chart_mode = chart.chart_mode

    def action_cycle_day_range(self) -> None:
        """Cycle through day ranges (7, 30, 90, 120)"""
        self.day_range_index = (self.day_range_index + 1) % len(self.day_ranges)
        self.day_range = self.day_ranges[self.day_range_index]

        # Update all panels
        banner = self.query_one(MarketIndices)
        chart = self.query_one("#chart", ChartPanel)
        technical = self.query_one("#technical", TechnicalPanel)
        watchlist = self.query_one("#watchlist", Watchlist)

        banner.update_range(self.day_range, self.selected_ticker)
        chart.update_range(self.day_range)
        technical.update_range(self.day_range)
        watchlist.update_range(self.day_range)

    def action_toggle_sort(self) -> None:
        """Toggle watchlist sort mode"""
        watchlist = self.query_one("#watchlist", Watchlist)
        watchlist.toggle_sort()

    def action_toggle_change_mode(self) -> None:
        """Toggle between day and range change display"""
        watchlist = self.query_one("#watchlist", Watchlist)
        watchlist.toggle_change_mode()

    def action_export_ta(self) -> None:
        """Copy technical analysis to clipboard"""
        import subprocess
        import re

        technical = self.query_one("#technical", TechnicalPanel)

        # Get the technical analysis text and strip Rich markup
        ta_text = technical.get_analysis_text()
        if not ta_text:
            return

        # Strip Rich markup tags (anything in square brackets)
        plain_text = re.sub(r'\[.*?\]', '', ta_text)

        # Copy to clipboard (macOS)
        try:
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            process.communicate(plain_text.encode('utf-8'))

            # Show confirmation in status bar
            status = self.query_one("#status_bar", StatusBar)
            status.update_status("Technical analysis copied to clipboard", None)
        except Exception as e:
            status = self.query_one("#status_bar", StatusBar)
            status.update_status(f"Failed to copy: {e}", "red")

    def action_update_prices(self) -> None:
        """Update prices for all watchlist tickers from Finnhub API"""
        # Run the update in a worker thread to avoid blocking the UI
        self.run_worker(self._update_prices_worker, thread=True)

    def _update_prices_worker(self) -> None:
        """Worker thread to fetch and update prices (runs in background)"""
        watchlist = self.query_one("#watchlist", Watchlist)
        tickers = [item.ticker for item in watchlist.items]

        total = len(tickers)
        success_count = 0

        # Update status bar to show progress
        status = self.query_one("#status_bar", StatusBar)

        for i, ticker in enumerate(tickers, 1):
            # Update progress in status bar (blue)
            self.call_from_thread(
                status.update_status,
                f"Updating prices... {i}/{total} ({ticker})",
                "blue"
            )

            # Fetch quote from Finnhub
            quote = self.finnhub.get_quote(ticker)

            if quote:
                # Insert/update in database
                if self.db.upsert_from_finnhub_quote(ticker, quote):
                    success_count += 1

        # Update complete - refresh all widgets
        self.call_from_thread(self._refresh_after_update, success_count, total)

    def _refresh_after_update(self, success_count: int, total: int) -> None:
        """Refresh UI after price update (called from worker thread)"""
        from datetime import datetime

        # Refresh all widgets that display prices
        watchlist = self.query_one("#watchlist", Watchlist)
        status = self.query_one("#status_bar", StatusBar)

        watchlist.refresh_prices()

        # Refresh market status as well
        status.refresh_market_status()

        # Update current ticker panels
        self.update_panels()

        # Show completion message with time and color
        time_str = datetime.now().strftime("%H:%M")

        if success_count == total:
            # All succeeded - white/default color
            message = f"Updated {success_count}/{total} at {time_str}"
            color = None
        else:
            # Some failed - red color
            message = f"Updated {success_count}/{total} at {time_str}"
            color = "red"

        status.update_status(message, color)
