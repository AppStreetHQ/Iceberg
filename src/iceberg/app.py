"""Main Iceberg Terminal application"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Header

from .config import Config
from .data.db import Database
from .widgets.market_indices import MarketIndices
from .widgets.ticker_banner import TickerBanner
from .widgets.watchlist import Watchlist
from .widgets.chart import ChartPanel
from .widgets.technical_panel import TechnicalPanel
from .widgets.status_bar import StatusBar


class IcebergApp(App):
    """Iceberg Terminal - Bloomberg-style stock market TUI"""

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
        Binding("q", "quit", "Quit", show=True),
    ]

    # Reactive state - automatically updates UI when changed
    selected_ticker = reactive("AAPL", init=False)
    day_range = reactive(90, init=False)  # 7, 30, 90, 120
    chart_mode = reactive("absolute", init=False)  # "absolute" or "relative"

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.db = Database(config.db_path)
        self.day_ranges = [7, 30, 90, 120]
        self.day_range_index = 2  # Start at 90 days

    def compose(self) -> ComposeResult:
        """Create child widgets"""
        yield Header(show_clock=True)
        yield MarketIndices(self.db, self.config.market_indices)

        with Horizontal(id="content"):
            with Vertical(id="left_panel"):
                yield TickerBanner(self.db, id="ticker_banner")
                yield Watchlist(self.db, self.config.watchlist_csv, id="watchlist")
            with Vertical(id="main_display"):
                yield ChartPanel(self.db, self.config.chart_height, id="chart")
                yield TechnicalPanel(self.db, id="technical")

        yield StatusBar(id="status_bar")

    def on_mount(self) -> None:
        """Initialize app on mount"""
        # Get first ticker from watchlist and select it
        watchlist = self.query_one("#watchlist", Watchlist)
        first_ticker = watchlist.get_selected_ticker()
        if first_ticker:
            self.selected_ticker = first_ticker
            self.update_panels()

    def on_watchlist_ticker_selected(self, message: Watchlist.TickerSelected) -> None:
        """Handle ticker selection from watchlist"""
        self.selected_ticker = message.ticker
        self.update_panels()

    def update_panels(self) -> None:
        """Update chart and technical panels with current ticker and range"""
        # Get company name from watchlist
        watchlist = self.query_one("#watchlist", Watchlist)
        selected_item = watchlist.get_selected_item()
        company_name = selected_item.name if selected_item else ""

        # Update ticker banner
        banner = self.query_one("#ticker_banner", TickerBanner)
        banner.update_ticker(self.selected_ticker, company_name)

        chart = self.query_one("#chart", ChartPanel)
        technical = self.query_one("#technical", TechnicalPanel)

        chart.update_ticker(self.selected_ticker, self.day_range)
        technical.update_ticker(self.selected_ticker, self.day_range)

        # Update status bar
        status = self.query_one("#status_bar", StatusBar)
        status.update_status(
            f"Viewing {self.selected_ticker} | Range: {self.day_range}d | Mode: {self.chart_mode}"
        )

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

        # Update status bar
        status = self.query_one("#status_bar", StatusBar)
        status.update_status(
            f"Chart mode: {self.chart_mode} | Range: {self.day_range}d"
        )

    def action_cycle_day_range(self) -> None:
        """Cycle through day ranges (7, 30, 90, 120)"""
        self.day_range_index = (self.day_range_index + 1) % len(self.day_ranges)
        self.day_range = self.day_ranges[self.day_range_index]

        # Update all panels
        banner = self.query_one("#ticker_banner", TickerBanner)
        chart = self.query_one("#chart", ChartPanel)
        technical = self.query_one("#technical", TechnicalPanel)
        watchlist = self.query_one("#watchlist", Watchlist)

        banner.update_range(self.day_range)
        chart.update_range(self.day_range)
        technical.update_range(self.day_range)
        watchlist.update_range(self.day_range)

        # Update status bar
        status = self.query_one("#status_bar", StatusBar)
        status.update_status(f"Day range changed to {self.day_range}d")

    def action_toggle_sort(self) -> None:
        """Toggle watchlist sort mode"""
        watchlist = self.query_one("#watchlist", Watchlist)
        sort_mode = watchlist.toggle_sort()

        # Update status bar
        status = self.query_one("#status_bar", StatusBar)
        mode_label = "Alphabetical" if sort_mode == "alpha" else "By % Change"
        status.update_status(f"Watchlist sorted: {mode_label}")

    def action_toggle_change_mode(self) -> None:
        """Toggle between day and range change display"""
        watchlist = self.query_one("#watchlist", Watchlist)
        change_mode = watchlist.toggle_change_mode()

        # Update status bar
        status = self.query_one("#status_bar", StatusBar)
        mode_label = "Daily Change" if change_mode == "day" else f"{self.day_range}d Range Change"
        status.update_status(f"Watchlist showing: {mode_label}")
