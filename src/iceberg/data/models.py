"""Data models for price data and watchlist items"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class DailyPrice:
    """Single day's OHLCV data"""

    ticker: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    adj_close: Optional[float]
    volume: int
    currency: str

    @classmethod
    def from_row(cls, row) -> "DailyPrice":
        """Create from SQLite row"""
        return cls(
            ticker=row["ticker"],
            trade_date=date.fromisoformat(row["trade_date"]),
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            adj_close=row["adj_close"],
            volume=row["volume"],
            currency=row["currency"],
        )


@dataclass
class Holding:
    """Portfolio holding"""

    ticker: str
    shares: float
    updated_at: str  # UTC timestamp

    @classmethod
    def from_row(cls, row) -> "Holding":
        """Create from SQLite row"""
        return cls(
            ticker=row["ticker"],
            shares=row["shares"],
            updated_at=row["updated_at_utc"],
        )


@dataclass
class WatchlistItem:
    """Item in the watchlist"""

    ticker: str
    name: str
    current_price: Optional[float] = None
    previous_close: Optional[float] = None
    range_start_price: Optional[float] = None  # Price at start of selected range
    range_change: Optional[float] = None  # Dollar change over range
    range_change_pct: Optional[float] = None  # Percentage change over range
    trade_score: Optional[int] = None  # Iceberg Trade Score (0-100)
    investment_score: Optional[int] = None  # Iceberg Investment Score (0-100)
    shares_held: float = 0.0  # Number of shares held in portfolio

    @property
    def price_change(self) -> Optional[float]:
        """Dollar change from previous close"""
        if self.current_price and self.previous_close:
            return self.current_price - self.previous_close
        return None

    @property
    def price_change_pct(self) -> Optional[float]:
        """Percentage change from previous close"""
        if (
            self.current_price
            and self.previous_close
            and self.previous_close != 0
        ):
            return (
                (self.current_price - self.previous_close) / self.previous_close
            ) * 100
        return None

    @property
    def is_gain(self) -> bool:
        """True if price is up"""
        change = self.price_change
        return change is not None and change > 0

    @property
    def is_loss(self) -> bool:
        """True if price is down"""
        change = self.price_change
        return change is not None and change < 0
