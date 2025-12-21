"""Load watchlist and other data from files"""

import csv
from pathlib import Path
from typing import List, Tuple


def load_watchlist_from_csv(csv_path: Path) -> List[Tuple[str, str]]:
    """
    Load watchlist from CSV (ticker, name)

    Args:
        csv_path: Path to CSV file

    Returns:
        List of (ticker, name) tuples
    """
    watchlist = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row.get('ticker', '').strip()
            name = row.get('name', '').strip()
            if ticker:  # Skip empty rows
                watchlist.append((ticker, name))
    return watchlist
