"""Finnhub API integration for market data

Free tier limits:
- 60 API calls/minute
- 1 year of historical data
- End-of-day prices + real-time quotes
"""

import os
import time
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path


class FinnhubClient:
    """Client for Finnhub API with rate limiting"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Finnhub client

        Args:
            api_key: Finnhub API key. If None, reads from .env file
        """
        if api_key is None:
            api_key = self._load_api_key()

        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1"
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests (safe rate)

    def _load_api_key(self) -> str:
        """Load API key from .env file"""
        env_path = Path(__file__).parent.parent.parent.parent / ".env"

        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('FINNHUB_API_KEY='):
                        return line.split('=', 1)[1]

        raise ValueError("FINNHUB_API_KEY not found in .env file")

    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make API request with rate limiting

        Args:
            endpoint: API endpoint (e.g., '/quote')
            params: Query parameters

        Returns:
            JSON response as dict
        """
        self._rate_limit()

        if params is None:
            params = {}

        params['token'] = self.api_key

        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, params=params)
        response.raise_for_status()

        return response.json()

    def get_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get real-time quote for a ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with quote data:
            - c: Current price
            - h: High price of the day
            - l: Low price of the day
            - o: Open price of the day
            - pc: Previous close price
            - t: Timestamp
        """
        try:
            data = self._request('/quote', {'symbol': ticker})
            return data
        except Exception as e:
            print(f"Error fetching quote for {ticker}: {e}")
            return None

    def get_candles(
        self,
        ticker: str,
        days: int = 365,
        resolution: str = 'D'
    ) -> Optional[Dict[str, List]]:
        """Get historical candle data (OHLCV)

        Args:
            ticker: Stock ticker symbol
            days: Number of days of history (max 365 for free tier)
            resolution: D (day), W (week), M (month)

        Returns:
            Dict with arrays:
            - c: List of close prices
            - h: List of high prices
            - l: List of low prices
            - o: List of open prices
            - t: List of timestamps
            - v: List of volumes
            - s: Status (ok/no_data)
        """
        try:
            # Calculate date range
            end_time = int(datetime.now().timestamp())
            start_time = int((datetime.now() - timedelta(days=days)).timestamp())

            data = self._request('/stock/candle', {
                'symbol': ticker,
                'resolution': resolution,
                'from': start_time,
                'to': end_time
            })

            if data.get('s') == 'no_data':
                print(f"No data available for {ticker}")
                return None

            return data
        except Exception as e:
            print(f"Error fetching candles for {ticker}: {e}")
            return None

    def get_company_profile(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get company profile/info

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with company info including name, industry, etc.
        """
        try:
            data = self._request('/stock/profile2', {'symbol': ticker})
            return data
        except Exception as e:
            print(f"Error fetching profile for {ticker}: {e}")
            return None
