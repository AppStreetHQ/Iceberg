"""SQLite database connection and queries"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional

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
