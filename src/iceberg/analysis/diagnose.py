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
    detect_recovery_pattern,
    detect_post_shock_recovery,
    detect_cheap_on_winner,
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

    # Check pattern triggers
    print(f"\n{'='*70}")
    print("PATTERN DETECTION")
    print(f"{'='*70}")

    recovery_detected = detect_recovery_pattern(
        current_price, sma10, sma50,
        trend10.bias if trend10 else None,
        trend50.bias if trend50 else None
    )
    print(f"Recovery Pattern (v1.0): {'✓ DETECTED' if recovery_detected else '✗ Not detected'}")
    if recovery_detected:
        print(f"  → Bonus: +20 (× {1.2 if resilience_count >= 3 else 0.8 if resilience_count == 0 else 1.0} resilience)")

    post_shock = detect_post_shock_recovery(
        current_price,
        distance_from_high,
        rsi.value if rsi else None,
        macd.hist if macd else None,
        long_term_trend,
        closes=closes,
        sma100=sma100
    )
    print(f"Post-Shock Recovery (v1.2): {'✓ DETECTED' if post_shock else '✗ Not detected'}")
    if post_shock:
        print(f"  → Bonus: +60 (× {1.2 if resilience_count >= 3 else 1.0} resilience)")
    else:
        # Show why it failed
        if distance_from_high is not None and distance_from_high > -10:
            print(f"  → Failed: Distance from high {distance_from_high:.1f}% (needs < -10%)")

        # Check historical strength
        if closes and sma100 and len(closes) >= 60:
            lookback = closes[-60:]
            had_strength = False
            for i in range(len(lookback)):
                window = closes[:-(60-i)] if i < 59 else closes
                if len(window) >= 100:
                    hist_sma100 = sum(window[-100:]) / 100
                    if lookback[i] > hist_sma100:
                        had_strength = True
                        break
            if not had_strength:
                print(f"  → Failed: Price was never above SMA(100) in past 60 days (no historical strength)")

        # Check early recovery signals
        rsi_ok = rsi and rsi.value > 20
        if closes and len(closes) >= 5:
            recent_low = min(closes[-5:])
            stabilizing = current_price >= recent_low * 0.98
        else:
            stabilizing = False

        if not (rsi_ok or stabilizing):
            print(f"  → Failed: No early recovery signals (RSI {rsi.value:.1f if rsi else 'N/A'} needs >20, or price needs to be stabilizing)")

    # Import the capitulation detection function
    from .scoring import detect_proven_winner_capitulation

    capitulation = detect_proven_winner_capitulation(
        current_price,
        closes,
        sma100,
        rsi.value if rsi else None,
        distance_from_high
    )
    print(f"Proven Winner Capitulation (v1.3): {'✓ DETECTED' if capitulation else '✗ Not detected'}")
    if capitulation:
        print(f"  → Trade Bonus: +120 (× {1.2 if resilience_count >= 3 else 1.0} resilience)")
        print(f"  → Investment Bonus: +100 (× {1.2 if resilience_count >= 3 else 1.0} resilience)")
        if sma50:
            print(f"  → Turnaround mode ACTIVE until price crosses ${sma50:.2f} (SMA 50)")

    cheap_winner = detect_cheap_on_winner(
        current_price,
        sma20,
        sma100,
        long_term_trend,
        rsi.value if rsi else None
    )
    print(f"Cheap on a Winner (v1.1): {'✓ DETECTED' if cheap_winner else '✗ Not detected'}")
    if cheap_winner:
        print(f"  → Bonus: +15")

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

    # Display scores (with turnaround if active)
    if trade_result.turnaround_active:
        print(f"🔥 TURNAROUND MODE ACTIVE (price below SMA(50): ${sma50:.2f})")
        print(f"\nTrade Score:")
        trade_label = get_rating_label(trade_result.turnaround_score)
        print(f"  Turnaround: {trade_result.turnaround_score}/100 ({trade_label}) ⚡")
        print(f"    Raw: {trade_result.turnaround_raw}")
        trade_bau_label = get_rating_label(trade_result.bau_score)
        print(f"  BAU: {trade_result.bau_score}/100 ({trade_bau_label})")
        print(f"    Raw: {trade_result.bau_raw}")
    else:
        trade_label = get_rating_label(trade_result.display_score)
        print(f"Trade Score: {trade_result.display_score}/100 ({trade_label})")
        print(f"  Raw score: {trade_result.display_raw}")

    print()

    if inv_result.turnaround_active:
        print(f"Investment Score:")
        inv_label = get_rating_label(inv_result.turnaround_score)
        print(f"  Turnaround: {inv_result.turnaround_score}/100 ({inv_label}) ⚡")
        print(f"    Raw: {inv_result.turnaround_raw}")
        inv_bau_label = get_rating_label(inv_result.bau_score)
        print(f"  BAU: {inv_result.bau_score}/100 ({inv_bau_label})")
        print(f"    Raw: {inv_result.bau_raw}")
    else:
        inv_label = get_rating_label(inv_result.display_score)
        print(f"Investment Score: {inv_result.display_score}/100 ({inv_label})")
        print(f"  Raw score: {inv_result.display_raw}")

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
