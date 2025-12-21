"""Formatting utilities for prices and display"""

from typing import Optional


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
