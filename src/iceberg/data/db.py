"""SQLite database connection and queries"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import DailyPrice


class Database:
    """SQLite database connection manager"""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
        try:
            yield conn
        finally:
            conn.close()

    def get_daily_prices(self, ticker: str, days: int) -> List[DailyPrice]:
        """Fetch last N days of price data for ticker"""
        with self.get_connection() as conn:
            query = """
                SELECT ticker, trade_date, open, high, low, close,
                       adj_close, volume, currency
                FROM prices_daily
                WHERE ticker = ?
                ORDER BY trade_date DESC
                LIMIT ?
            """
            cursor = conn.execute(query, (ticker, days))
            rows = cursor.fetchall()
            # Reverse to get oldest to newest
            return [DailyPrice.from_row(row) for row in reversed(rows)]

    def get_latest_price(self, ticker: str) -> Optional[DailyPrice]:
        """Get most recent price for ticker"""
        with self.get_connection() as conn:
            query = """
                SELECT ticker, trade_date, open, high, low, close,
                       adj_close, volume, currency
                FROM prices_daily
                WHERE ticker = ?
                ORDER BY trade_date DESC
                LIMIT 1
            """
            cursor = conn.execute(query, (ticker,))
            row = cursor.fetchone()
            return DailyPrice.from_row(row) if row else None

    def get_previous_close(self, ticker: str) -> Optional[float]:
        """Get previous day's closing price (for % change calc)"""
        with self.get_connection() as conn:
            query = """
                SELECT close
                FROM prices_daily
                WHERE ticker = ?
                ORDER BY trade_date DESC
                LIMIT 1 OFFSET 1
            """
            cursor = conn.execute(query, (ticker,))
            row = cursor.fetchone()
            return row[0] if row else None

    def get_closing_prices(self, ticker: str, days: int) -> List[float]:
        """Get list of closing prices for technical analysis"""
        prices = self.get_daily_prices(ticker, days)
        return [p.close for p in prices]

    def upsert_daily_price(
        self,
        ticker: str,
        trade_date: str,  # YYYY-MM-DD
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        adj_close: Optional[float] = None,
        currency: str = "USD",
        source: str = "finnhub",
    ) -> None:
        """Insert or update daily price data (single entry per date)

        Uses INSERT OR REPLACE to ensure only one entry per ticker+date.
        Updates existing entry if it exists, inserts if it doesn't.
        """
        with self.get_connection() as conn:
            fetched_at_utc = datetime.utcnow().isoformat()

            query = """
                INSERT OR REPLACE INTO prices_daily (
                    ticker, trade_date, open, high, low, close,
                    adj_close, volume, currency, source, fetched_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            conn.execute(
                query,
                (
                    ticker,
                    trade_date,
                    open_price,
                    high,
                    low,
                    close,
                    adj_close,
                    volume,
                    currency,
                    source,
                    fetched_at_utc,
                ),
            )
            conn.commit()

    def upsert_from_finnhub_quote(
        self, ticker: str, quote_data: Dict[str, Any]
    ) -> bool:
        """Convenience method to insert Finnhub quote data

        Finnhub quote structure:
        - c: Current price (close)
        - h: High price of the day
        - l: Low price of the day
        - o: Open price of the day
        - pc: Previous close price
        - t: Timestamp

        Returns:
            True if successfully inserted, False if data invalid
        """
        # Validate required fields are present
        required = ["c", "h", "l", "o", "t"]
        if not all(k in quote_data for k in required):
            return False

        # Skip if price is 0 (market closed, no data)
        if quote_data["c"] == 0:
            return False

        # Convert timestamp to date (Finnhub uses Unix timestamp)
        trade_date = datetime.fromtimestamp(quote_data["t"]).strftime("%Y-%m-%d")

        # Note: Finnhub doesn't provide volume in quote endpoint
        # We'll use 0 as placeholder (volume available in candles endpoint)
        self.upsert_daily_price(
            ticker=ticker,
            trade_date=trade_date,
            open_price=quote_data["o"],
            high=quote_data["h"],
            low=quote_data["l"],
            close=quote_data["c"],
            volume=0,  # Not available in quote endpoint
            adj_close=None,
            currency="USD",
            source="finnhub",
        )

        return True
