"""Configuration management for Iceberg Terminal"""

from pathlib import Path
from typing import Optional


class Config:
    """Application configuration"""

    def __init__(self):
        # Default paths relative to project root
        project_root = Path(__file__).parent.parent.parent

        # Database and data paths (shared with StockStreet)
        self.db_path = project_root / ".." / "StockStreet" / "Data" / "stockstreet.sqlite"
        self.watchlist_csv = project_root / ".." / "StockStreet" / "Data" / "nasdaq100.csv"

        # Display settings
        self.default_day_range = 30
        self.chart_height = 15
        self.theme = "dark"

        # Market indices to display
        self.market_indices = ["SPY", "QQQ", "DIA", "IWM"]

    def resolve_paths(self):
        """Resolve relative paths to absolute and validate they exist"""
        self.db_path = self.db_path.resolve()
        self.watchlist_csv = self.watchlist_csv.resolve()

        # Validate paths exist
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database not found: {self.db_path}\n"
                f"Expected at: ../StockStreet/Data/stockstreet.sqlite"
            )
        if not self.watchlist_csv.exists():
            raise FileNotFoundError(
                f"Watchlist CSV not found: {self.watchlist_csv}\n"
                f"Expected at: ../StockStreet/Data/nasdaq100.csv"
            )

        return self

    @classmethod
    def load(cls) -> 'Config':
        """Load and validate configuration"""
        config = cls()
        config.resolve_paths()
        return config
