"""Formatting utilities for prices and display"""

from typing import Optional

# Color constants - single source of truth
COLOR_GAIN = "#00ff00"  # Bright green
COLOR_LOSS = "#ff0000"  # Bright red
COLOR_NEUTRAL = "#888888"  # Gray


def format_price(price: Optional[float], decimals: int = 2) -> str:
    """Format price with currency symbol"""
    if price is None:
        return "N/A"
    return f"${price:,.{decimals}f}"


def format_change(change: Optional[float], decimals: int = 2) -> str:
    """Format price change with +/- sign"""
    if change is None:
        return "N/A"
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.{decimals}f}"


def format_change_pct(change_pct: Optional[float], decimals: int = 2) -> str:
    """Format percentage change with +/- sign and %"""
    if change_pct is None:
        return "N/A"
    sign = "+" if change_pct >= 0 else ""
    return f"{sign}{change_pct:.{decimals}f}%"


def get_arrow(change: Optional[float]) -> str:
    """Get arrow indicator for price change"""
    if change is None or change == 0:
        return "→"
    return "▲" if change > 0 else "▼"


def get_change_class(change: Optional[float]) -> str:
    """Get CSS class for price change color"""
    if change is None or change == 0:
        return "neutral"
    return "gain" if change > 0 else "loss"


def format_market_cap(market_cap: Optional[float], currency: str = "USD") -> str:
    """Format market cap with M/B/T suffix and 3 decimal places

    Args:
        market_cap: Market capitalization value
        currency: Currency code (e.g., "USD", "EUR")

    Returns:
        Formatted string like "41.424B USD" or "4.472T USD"
    """
    if market_cap is None or market_cap == 0:
        return "N/A"

    # Determine suffix and divisor
    if market_cap >= 1_000_000_000_000:  # Trillions
        value = market_cap / 1_000_000_000_000
        suffix = "T"
    elif market_cap >= 1_000_000_000:  # Billions
        value = market_cap / 1_000_000_000
        suffix = "B"
    elif market_cap >= 1_000_000:  # Millions
        value = market_cap / 1_000_000
        suffix = "M"
    else:
        # Less than a million - show as-is
        return f"{market_cap:,.0f} {currency}"

    return f"{value:.3f}{suffix} {currency}"
