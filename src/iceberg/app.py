"""Main Iceberg Terminal application"""

from typing import Optional, Dict, Any
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Header
from textual.worker import Worker, WorkerState
from textual.timer import Timer

from .config import Config
from .data.db import Database
from .api.finnhub import FinnhubClient
from .widgets.market_indices import MarketIndices
from .widgets.ticker_banner import TickerBanner
from .widgets.watchlist import Watchlist
from .widgets.chart import ChartPanel
from .widgets.technical_panel import TechnicalPanel
from .widgets.scores_panel import ScoresPanel
from .widgets.status_bar import StatusBar
from .widgets.portfolio_summary import PortfolioSummary
from .widgets.holdings_dialog import HoldingsInputDialog


class IcebergApp(App):
    """Iceberg Terminal v1.0 - Bloomberg-style stock market TUI"""

    CSS_PATH = "app.tcss"
    SHOW_FOOTER = False  # Disable built-in footer, we have custom StatusBar

    BINDINGS = [
        Binding("j", "watchlist_down", "Next ticker", show=False),
        Binding("k", "watchlist_up", "Previous ticker", show=False),
        Binding("down", "watchlist_down", "Next ticker", show=False),
        Binding("up", "watchlist_up", "Previous ticker", show=False),
        Binding("space", "toggle_comparison", "Mark compare", show=True),
        Binding("c", "toggle_chart_mode", "Toggle chart mode", show=True),
        Binding("r", "cycle_day_range", "Cycle day range", show=True),
        Binding("s", "toggle_sort", "Toggle sort", show=True),
        Binding("d", "toggle_change_mode", "Toggle day/range", show=True),
        Binding("e", "export_ta", "Copy TA", show=True),
        Binding("u", "update_prices", "Update prices", show=True),
        Binding("p", "edit_holding", "Edit holding", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    # Reactive state - automatically updates UI when changed
    selected_ticker = reactive("AAPL", init=False)
    day_range = reactive(120, init=False)  # 7, 30, 90, 120
    chart_mode = reactive("absolute", init=False)  # "absolute" or "relative"
    comparison_ticker = reactive(None, init=False)  # Optional ticker marked for comparison

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.db = Database(config.db_path)
        self.finnhub = FinnhubClient()
        self.day_ranges = [7, 30, 90, 120, 180]
        self.day_range_index = 3  # Start at 120 days
        self.profile_cache = {}  # Cache company profiles by ticker

        # Auto-refresh and market status state
        self.auto_refresh_timer: Optional[Timer] = None
        self.last_market_state: Optional[Dict[str, Any]] = None
        self.closing_refresh_done: bool = False
        self._update_worker: Optional[Worker] = None  # Track active worker for debouncing
        self._is_auto_refresh: bool = False  # Track if current refresh is auto or manual

    def compose(self) -> ComposeResult:
        """Create child widgets"""
        yield Header(show_clock=True)
        yield MarketIndices(self.db, self.config.market_indices)

        with Horizontal(id="content"):
            with Vertical(id="left_panel"):
                yield TickerBanner(self.db, id="ticker_banner")
                yield Watchlist(self.db, self.config.watchlist_csv, self.day_range, id="watchlist")
                yield PortfolioSummary(self.db, id="portfolio_summary")
            with Vertical(id="main_display"):
                yield ChartPanel(self.db, self.config.chart_height, self.day_range, id="chart")
                yield TechnicalPanel(self.db, self.day_range, id="technical")
                yield ScoresPanel(self.db, self.day_range, id="scores")

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

        # Initialize market state and check status immediately
        self._check_market_status()

        # Start auto-refresh timer (5 minutes = 300 seconds)
        self.auto_refresh_timer = self.set_interval(300, self._auto_refresh_callback)

        # Trigger immediate price refresh on startup (respects market hours)
        self.action_update_prices()

    def on_watchlist_ticker_selected(self, message: Watchlist.TickerSelected) -> None:
        """Handle ticker selection from watchlist"""
        self.selected_ticker = message.ticker
        self.update_panels()

    def on_option_list_option_highlighted(self, event) -> None:
        """Handle ticker highlight changes (from arrow keys or j/k navigation)"""
        # Only handle events from the watchlist's option list
        if event.option_list.id == "ticker_list":
            watchlist = self.query_one("#watchlist", Watchlist)
            ticker = watchlist.get_selected_ticker()
            if ticker and ticker != self.selected_ticker:
                self.selected_ticker = ticker
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
        scores = self.query_one("#scores", ScoresPanel)

        chart.update_ticker(self.selected_ticker, self.day_range)
        chart.update_comparison(self.comparison_ticker)  # Preserve comparison state
        technical.update_ticker(self.selected_ticker, self.day_range)
        scores.update_ticker(self.selected_ticker, self.day_range)

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
        scores = self.query_one("#scores", ScoresPanel)
        watchlist = self.query_one("#watchlist", Watchlist)

        banner.update_range(self.day_range, self.selected_ticker)
        chart.update_range(self.day_range)
        technical.update_range(self.day_range)
        scores.update_range(self.day_range)
        watchlist.update_range(self.day_range)

    def action_toggle_sort(self) -> None:
        """Toggle watchlist sort mode"""
        watchlist = self.query_one("#watchlist", Watchlist)
        watchlist.toggle_sort()

    def action_toggle_change_mode(self) -> None:
        """Toggle between day and range change display"""
        watchlist = self.query_one("#watchlist", Watchlist)
        watchlist.toggle_change_mode()

    def action_toggle_comparison(self) -> None:
        """Toggle comparison ticker for currently highlighted ticker in watchlist"""
        watchlist = self.query_one("#watchlist", Watchlist)

        # Get the currently viewed ticker (not the highlighted one)
        ticker = self.selected_ticker

        if not ticker:
            return

        # Toggle logic:
        # - If this ticker is already marked: toggle it off
        # - If a different ticker is marked (or none): mark this one
        if self.comparison_ticker == ticker:
            self.comparison_ticker = None
            status_msg = "Comparison cleared"
        else:
            self.comparison_ticker = ticker
            status_msg = f"Marked {ticker} for comparison"

        self.update_comparison_panels()

        status = self.query_one("#status_bar", StatusBar)
        status.update_status(status_msg, "cyan" if self.comparison_ticker else None)

    def update_comparison_panels(self) -> None:
        """Update panels when comparison state changes"""
        chart = self.query_one("#chart", ChartPanel)
        watchlist = self.query_one("#watchlist", Watchlist)

        # Update watchlist first to preserve selection, then chart
        watchlist.set_comparison_ticker(self.comparison_ticker)
        chart.update_comparison(self.comparison_ticker)

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

    def action_edit_holding(self) -> None:
        """Edit holdings for currently selected ticker"""
        # Get currently selected ticker
        ticker = self.selected_ticker
        if not ticker:
            status = self.query_one("#status_bar", StatusBar)
            status.update_status("No ticker selected", "yellow")
            return

        # Get current holding
        current_shares = self.db.get_holding(ticker)

        # Define callback for when dialog is dismissed
        def handle_result(shares: Optional[float]) -> None:
            """Callback when dialog is dismissed"""
            status = self.query_one("#status_bar", StatusBar)

            if shares is not None:
                # Update database
                if self.db.upsert_holding(ticker, shares):
                    # Refresh watchlist to show new holding
                    watchlist = self.query_one("#watchlist", Watchlist)
                    watchlist.refresh_prices()

                    # Refresh portfolio summary
                    portfolio = self.query_one("#portfolio_summary", PortfolioSummary)
                    portfolio.refresh_portfolio()

                    if shares == 0:
                        status.update_status(f"Cleared holding for {ticker}", "green")
                    else:
                        status.update_status(
                            f"Set {ticker} holding to {shares:.2f} shares", "green"
                        )
                else:
                    status.update_status(f"Failed to update holding for {ticker}", "red")
            else:
                status.update_status("Cancelled", "yellow")

        # Show dialog
        self.push_screen(HoldingsInputDialog(ticker, current_shares), handle_result)

    def _check_market_status(self) -> Optional[Dict[str, Any]]:
        """Check current market status and update state

        Returns:
            Market status dict or None if unavailable
        """
        market_status = self.finnhub.get_market_status('US')

        if market_status:
            # Store current status for next comparison
            self.last_market_state = market_status

        return market_status

    def _should_refresh_prices(self, market_status: Optional[Dict[str, Any]]) -> tuple[bool, str]:
        """Determine if prices should be refreshed based on market status

        Returns:
            Tuple of (should_refresh: bool, reason: str)
        """
        if not market_status:
            # Can't determine market status - refresh anyway (fail open)
            return True, "Market status unavailable"

        is_open = market_status.get('isOpen', False)
        session = market_status.get('session', 'unknown')

        # Market is open (regular hours, pre-market, or after-hours)
        if is_open:
            self.closing_refresh_done = False  # Reset flag when market opens
            return True, f"Market {session}"

        # Market is closed
        # Check if we just transitioned from open to closed
        if self.last_market_state and self.last_market_state.get('isOpen', False):
            # Just closed - do one final refresh to capture closing prices
            self.closing_refresh_done = True
            return True, "Market just closed - capturing final prices"

        # Market has been closed
        if self.closing_refresh_done:
            # Already captured closing prices - skip refresh
            return False, "Market closed - closing prices already captured"
        else:
            # Market was already closed at app start - do one refresh
            self.closing_refresh_done = True
            return True, "Capturing latest closing prices"

    def action_update_prices(self) -> None:
        """Update prices for all watchlist tickers from Finnhub API"""
        status = self.query_one("#status_bar", StatusBar)

        # Check if update is already in progress (debouncing)
        if self._update_worker and self._update_worker.state == WorkerState.RUNNING:
            status.update_status("Update already in progress", "yellow")
            return

        # Check market status first
        market_status = self._check_market_status()
        should_refresh, reason = self._should_refresh_prices(market_status)

        if not should_refresh:
            # Show skip message in cyan
            status.update_status(f"Skipped: {reason}", "cyan")
            return

        # Show reason for refresh in blue
        status.update_status(f"Updating prices... ({reason})", "blue")

        # Run the update in a worker thread to avoid blocking the UI
        self._is_auto_refresh = False  # Manual refresh
        self._update_worker = self.run_worker(self._update_prices_worker, thread=True)

    def _auto_refresh_callback(self) -> None:
        """Callback for auto-refresh timer (runs every 5 minutes)

        Called by Textual's set_interval timer. Checks market status
        and conditionally refreshes prices.
        """
        status = self.query_one("#status_bar", StatusBar)

        # Check if update is already in progress (debouncing)
        if self._update_worker and self._update_worker.state == WorkerState.RUNNING:
            # Skip this auto-refresh cycle, worker is still running
            return

        # Check market status
        market_status = self._check_market_status()
        should_refresh, reason = self._should_refresh_prices(market_status)

        if not should_refresh:
            # Update status bar to show we checked but skipped
            from datetime import datetime
            time_str = datetime.now().strftime("%H:%M")
            status.update_status(f"Auto-check at {time_str}: {reason}", "dim white")

            # Refresh market status display in status bar
            status.refresh_market_status()
            return

        # Refresh prices - reuse existing worker
        status.update_status(f"Auto-updating... ({reason})", "blue")
        self._is_auto_refresh = True  # Auto refresh
        self._update_worker = self.run_worker(self._update_prices_worker, thread=True)

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
        self.call_from_thread(self._refresh_after_update, success_count, total, self._is_auto_refresh)

    def _refresh_after_update(self, success_count: int, total: int, is_auto: bool = False) -> None:
        """Refresh UI after price update (called from worker thread)

        Args:
            success_count: Number of successful price updates
            total: Total number of tickers attempted
            is_auto: True if this was triggered by auto-refresh, False if manual
        """
        from datetime import datetime

        # Refresh all widgets that display prices
        watchlist = self.query_one("#watchlist", Watchlist)
        status = self.query_one("#status_bar", StatusBar)

        watchlist.refresh_prices()

        # Refresh portfolio summary
        portfolio = self.query_one("#portfolio_summary", PortfolioSummary)
        portfolio.refresh_portfolio()

        # Refresh market status as well
        status.refresh_market_status()

        # Update current ticker panels
        self.update_panels()

        # Show completion message with time and color
        time_str = datetime.now().strftime("%H:%M")
        refresh_type = "Auto-updated" if is_auto else "Updated"

        if success_count == total:
            # All succeeded - white/default color
            message = f"{refresh_type} {success_count}/{total} at {time_str}"
            color = None
        else:
            # Some failed - red color
            message = f"{refresh_type} {success_count}/{total} at {time_str}"
            color = "red"

        status.update_status(message, color)
