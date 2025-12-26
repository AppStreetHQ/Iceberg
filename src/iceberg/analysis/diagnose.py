"""
Diagnostic tool to investigate scoring on specific dates

Usage: python -m iceberg.analysis.diagnose TICKER YYYY-MM-DD
"""

import sys
from datetime import datetime
from pathlib import Path

from ..config import Config
from ..data.db import Database
from .indicators import (
    compute_macd,
    compute_rsi,
    compute_sma,
    compute_trend,
    compute_volatility,
    compute_distance_from_high,
    count_recovery_patterns,
    compute_long_term_trend,
)
from .scoring import (
    calculate_trade_score,
    calculate_investment_score,
    get_rating_label,
)


def diagnose_date(ticker: str, target_date: str):
    """
    Diagnose scoring for a specific ticker and date.

    Args:
        ticker: Stock ticker symbol
        target_date: Date in YYYY-MM-DD format
    """
    # Load config and database
    config = Config.load()
    db = Database(config.db_path)

    # Parse target date
    date_obj = datetime.strptime(target_date, '%Y-%m-%d')

    print(f"\n{'='*70}")
    print(f"Diagnostic Report: {ticker} on {target_date}")
    print(f"{'='*70}\n")

    # Fetch price data up to target date
    with db.get_connection() as conn:
        query = """
            SELECT close, trade_date
            FROM prices_daily
            WHERE ticker = ?
            AND trade_date < ?
            ORDER BY trade_date DESC
            LIMIT 365
        """
        cursor = conn.execute(query, (ticker, target_date))
        rows = cursor.fetchall()

    if not rows or len(rows) < 50:
        print(f"Insufficient data for {ticker} before {target_date}")
        return

    # Reverse to chronological order
    closes = [row[0] for row in reversed(rows)]
    dates = [row[1] for row in reversed(rows)]

    print(f"Data points available: {len(closes)}")
    print(f"Date range: {dates[0]} to {dates[-1]}")
    print(f"\n{'='*70}")
    print("PRICE DATA")
    print(f"{'='*70}")
    print(f"Current price: ${closes[-1]:.2f}")
    if len(closes) >= 2:
        print(f"Previous price: ${closes[-2]:.2f}")
        change = closes[-1] - closes[-2]
        change_pct = (change / closes[-2]) * 100
        print(f"1-day change: ${change:+.2f} ({change_pct:+.2f}%)")

    # Calculate all indicators
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

    # Print indicators
    print(f"\n{'='*70}")
    print("INDICATORS")
    print(f"{'='*70}")

    if macd:
        print(f"MACD: {macd.macd:.2f}, Signal: {macd.signal:.2f}, Hist: {macd.hist:.2f}, Bias: {macd.bias.value}")
    else:
        print("MACD: N/A")

    if rsi:
        print(f"RSI(14): {rsi.value:.1f}, Bias: {rsi.bias.value}")
    else:
        print("RSI(14): N/A")

    print(f"\nSMA(10): ${sma10:.2f}" if sma10 else "SMA(10): N/A")
    if sma10:
        diff10 = ((current_price - sma10) / sma10) * 100
        print(f"  Distance: {diff10:+.2f}%")

    print(f"SMA(20): ${sma20:.2f}" if sma20 else "SMA(20): N/A")
    if sma20:
        diff20 = ((current_price - sma20) / sma20) * 100
        print(f"  Distance: {diff20:+.2f}%")

    print(f"SMA(50): ${sma50:.2f}" if sma50 else "SMA(50): N/A")
    if sma50:
        diff50 = ((current_price - sma50) / sma50) * 100
        print(f"  Distance: {diff50:+.2f}%")

    print(f"SMA(100): ${sma100:.2f}" if sma100 else "SMA(100): N/A")
    if sma100:
        diff100 = ((current_price - sma100) / sma100) * 100
        print(f"  Distance: {diff100:+.2f}%")

    if trend10:
        print(f"\nTrend(10): {trend10.bias.value}, Delta: {trend10.delta_pct:+.2f}%")
    if trend50:
        print(f"Trend(50): {trend50.bias.value}, Delta: {trend50.delta_pct:+.2f}%")
    if long_term_trend:
        print(f"Trend(100): {long_term_trend.value}")

    if volatility:
        print(f"\nVolatility: {volatility.bias.value}, Sigma: {volatility.sigma:.2f}%")

    print(f"\nDistance from 20d high: {distance_from_high:+.2f}%" if distance_from_high else "Distance from high: N/A")
    print(f"Resilience count (6mo): {resilience_count} recoveries")

    # v1.4 Innovation Growth Indicators
    from .indicators import (
        compute_rally_magnitude,
        compute_growth_rate,
        compute_return_to_highs_frequency,
        compute_trend_slope
    )

    print(f"\n{'='*70}")
    print("INNOVATION GROWTH METRICS (v1.4)")
    print(f"{'='*70}")

    rally_mag = compute_rally_magnitude(closes, 90)
    if rally_mag is not None:
        print(f"Rally Magnitude (90d): {rally_mag:+.1f}% (largest trough-to-peak)")
    else:
        print("Rally Magnitude: N/A")

    growth_rate = compute_growth_rate(closes, 252) if len(closes) >= 252 else None
    if growth_rate is not None:
        print(f"Growth Rate (1yr): {growth_rate:+.1f}% annualized")
    else:
        print("Growth Rate (1yr): N/A")

    return_to_highs = compute_return_to_highs_frequency(closes, 180)
    if return_to_highs is not None:
        print(f"Return to Highs Frequency: {return_to_highs:.1f}% of time near highs")
    else:
        print("Return to Highs: N/A")

    trend_slope = compute_trend_slope(closes, 100)
    if trend_slope is not None:
        print(f"Trend Slope (100d): {trend_slope:+.1f}% annualized steepness")
    else:
        print("Trend Slope: N/A")

    # Calculate scores
    print(f"\n{'='*70}")
    print("SCORING")
    print(f"{'='*70}")

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
        closes=closes
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

    # Display scores
    trade_label = get_rating_label(trade_result.display_score, is_trade_score=True)
    print(f"Trade Score: {trade_result.display_score}/100 ({trade_label})")

    inv_label = get_rating_label(inv_result.display_score, is_trade_score=False)
    print(f"Investment Score: {inv_result.display_score}/100 ({inv_label})")

    print(f"\n{'='*70}\n")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("\nUsage: python -m iceberg.analysis.diagnose TICKER YYYY-MM-DD")
        print("\nExample:")
        print("  python -m iceberg.analysis.diagnose META 2025-11-21")
        print()
        sys.exit(1)

    ticker = sys.argv[1].upper()
    date = sys.argv[2]

    diagnose_date(ticker, date)
