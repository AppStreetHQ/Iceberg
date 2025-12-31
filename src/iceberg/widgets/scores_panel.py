"""Iceberg Scores panel widget"""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Static
from typing import Optional
from rich.text import Text

from ..data.db import Database
from ..analysis.indicators import (
    compute_macd,
    compute_rsi,
    compute_sma,
    compute_trend,
    compute_volatility,
    compute_distance_from_high,
    count_recovery_patterns,
    compute_long_term_trend,
    find_support_resistance,
)
from ..analysis.scoring import (
    calculate_trade_score,
    calculate_investment_score,
    get_rating_label,
    get_rating_color,
    generate_score_bar,
)


class ScoresPanel(Widget):
    """Iceberg Scores display panel"""

    def __init__(self, db: Database, day_range: int = 120, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.current_ticker: Optional[str] = None
        self.current_range = day_range

    def compose(self) -> ComposeResult:
        """Compose the scores panel"""
        with VerticalScroll(id="scores_container"):
            yield Static("", id="scores_display")

    def update_ticker(self, ticker: str, day_range: Optional[int] = None) -> None:
        """Update scores for new ticker"""
        self.current_ticker = ticker
        if day_range is not None:
            self.current_range = day_range
        self.render_scores()

    def update_range(self, day_range: int) -> None:
        """Update day range"""
        self.current_range = day_range
        if self.current_ticker:
            self.render_scores()

    def render_scores(self) -> None:
        """Render Iceberg scores"""
        if not self.current_ticker:
            return

        # Fetch closing prices - use 365 days for consistent calculation
        data_days = 365
        closes = self.db.get_closing_prices(self.current_ticker, data_days)

        if not closes or len(closes) < 20:
            self.query_one("#scores_display", Static).update(
                f"Insufficient data for {self.current_ticker} scores"
            )
            return

        # Compute all indicators needed for scoring
        current_price = closes[-1]
        macd = compute_macd(closes)
        rsi = compute_rsi(closes, 14)
        sma10 = compute_sma(closes, 10)
        sma20 = compute_sma(closes, 20)
        sma50 = compute_sma(closes, 50)
        sma100 = compute_sma(closes, 100)
        trend10 = compute_trend(closes, 10)
        trend50 = compute_trend(closes, 50)
        long_term_trend = compute_long_term_trend(closes, 100)
        volatility = compute_volatility(closes)
        distance_from_high = compute_distance_from_high(closes, 20)
        resilience_count = count_recovery_patterns(closes, 180)
        support, resistance = find_support_resistance(closes, window=5)

        # Calculate both scores
        trade_result = calculate_trade_score(
            current_price=current_price,
            macd_bias=macd.bias if macd else None,
            macd_hist=macd.hist if macd else None,
            rsi_value=rsi.value if rsi else None,
            rsi_bias=rsi.bias if rsi else None,
            sma10=sma10,
            sma20=sma20,
            sma50=sma50,
            sma100=sma100,
            trend10_bias=trend10.bias if trend10 else None,
            trend50_bias=trend50.bias if trend50 else None,
            long_term_trend=long_term_trend,
            volatility_bias=volatility.bias if volatility else None,
            distance_from_high=distance_from_high,
            resilience_count=resilience_count,
            closes=closes,
            support=support,
            resistance=resistance
        )

        inv_result = calculate_investment_score(
            current_price=current_price,
            macd_bias=macd.bias if macd else None,
            macd_hist=macd.hist if macd else None,
            rsi_value=rsi.value if rsi else None,
            rsi_bias=rsi.bias if rsi else None,
            sma10=sma10,
            sma20=sma20,
            sma50=sma50,
            sma100=sma100,
            trend10_bias=trend10.bias if trend10 else None,
            trend50_bias=trend50.bias if trend50 else None,
            long_term_trend=long_term_trend,
            volatility_bias=volatility.bias if volatility else None,
            distance_from_high=distance_from_high,
            resilience_count=resilience_count,
            closes=closes
        )

        # Build display
        display = Text()

        display.append("Iceberg™ Score System v2.1", style="#00ffff")
        display.append("\n\n")

        # Trade Score
        trade_score = trade_result.display_score
        trade_label = get_rating_label(trade_score, is_trade_score=True)
        trade_color = get_rating_color(trade_score)
        trade_bar = generate_score_bar(trade_score, width=20)
        trade_suffix = " ⚡" if trade_result.turnaround_active else ""

        display.append("Trade Score:      ", style="bold white")
        display.append(f"{trade_score:>3}/100 ", style=trade_color)
        display.append(trade_bar, style=trade_color)
        display.append(f"  {trade_label}{trade_suffix}", style=trade_color)
        display.append("\n")

        # Investment Score
        inv_score = inv_result.display_score
        inv_label = get_rating_label(inv_score, is_trade_score=False)
        inv_color = get_rating_color(inv_score)
        inv_bar = generate_score_bar(inv_score, width=20)
        inv_suffix = " ⚡" if inv_result.turnaround_active else ""

        display.append("Investment Score: ", style="bold white")
        display.append(f"{inv_score:>3}/100 ", style=inv_color)
        display.append(inv_bar, style=inv_color)
        display.append(f"  {inv_label}{inv_suffix}", style=inv_color)
        display.append("\n")

        # Update display
        self.query_one("#scores_display", Static).update(display)
