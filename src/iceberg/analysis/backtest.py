"""
Back-testing module for Iceberg Score System

Tests historical accuracy of Trade Score and Investment Score predictions
by calculating scores at regular intervals and measuring forward returns.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from collections import defaultdict

from ..data.db import Database
from .indicators import compute_macd, compute_rsi, compute_sma, compute_trend, compute_volatility
from .scoring import calculate_trade_score, calculate_investment_score, get_rating_label


@dataclass
class BacktestResult:
    """Single back-test data point"""
    date: str
    price: float
    trade_score: int
    investment_score: int
    trade_rating: str
    investment_rating: str
    return_2w: Optional[float] = None  # 2-week forward return (%)
    return_1m: Optional[float] = None  # 1-month forward return (%)
    return_3m: Optional[float] = None  # 3-month forward return (%)


@dataclass
class AccuracyStats:
    """Accuracy statistics for a rating tier"""
    rating: str
    count: int
    positive_rate_2w: float  # % of times 2w return was positive
    avg_return_2w: float
    positive_rate_1m: float
    avg_return_1m: float
    positive_rate_3m: float
    avg_return_3m: float


def calculate_score_at_date(
    ticker: str,
    as_of_date: datetime,
    db: Database,
    lookback_days: int = 365
) -> Optional[Tuple[int, int]]:
    """
    Calculate Iceberg Scores as of a specific historical date.

    Uses only data available BEFORE the as_of_date (no look-ahead bias).

    Args:
        ticker: Stock ticker symbol
        as_of_date: Calculate scores as of this date
        db: Database connection
        lookback_days: Days of history to use for calculation

    Returns:
        Tuple of (trade_score, investment_score) or None if insufficient data
    """
    # Fetch prices up to (but not including) as_of_date
    # We need lookback_days + buffer for indicator calculation
    with db.get_connection() as conn:
        query = """
            SELECT close
            FROM prices_daily
            WHERE ticker = ?
            AND trade_date < ?
            ORDER BY trade_date DESC
            LIMIT ?
        """
        cursor = conn.execute(
            query,
            (ticker, as_of_date.strftime('%Y-%m-%d'), lookback_days + 50)
        )
        rows = cursor.fetchall()

    if not rows or len(rows) < 50:
        return None

    # Reverse to chronological order
    closes = [row[0] for row in reversed(rows)]

    # Take only lookback_days (most recent)
    closes = closes[-lookback_days:] if len(closes) > lookback_days else closes

    if len(closes) < 50:  # Need minimum data for indicators
        return None

    # Calculate indicators
    current_price = closes[-1]
    macd = compute_macd(closes)
    rsi = compute_rsi(closes, 14)
    sma10 = compute_sma(closes, 10)
    sma50 = compute_sma(closes, 50)
    trend10 = compute_trend(closes, 10)
    trend50 = compute_trend(closes, 50)
    volatility = compute_volatility(closes)

    # Calculate scores
    trade_raw, trade_score = calculate_trade_score(
        current_price=current_price,
        macd_bias=macd.bias if macd else None,
        rsi_value=rsi.value if rsi else None,
        rsi_bias=rsi.bias if rsi else None,
        sma10=sma10,
        trend10_bias=trend10.bias if trend10 else None,
        sma50=sma50,
        trend50_bias=trend50.bias if trend50 else None,
        volatility_bias=volatility.bias if volatility else None
    )

    inv_raw, inv_score = calculate_investment_score(
        current_price=current_price,
        macd_bias=macd.bias if macd else None,
        rsi_value=rsi.value if rsi else None,
        rsi_bias=rsi.bias if rsi else None,
        sma10=sma10,
        sma50=sma50,
        trend10_bias=trend10.bias if trend10 else None,
        trend50_bias=trend50.bias if trend50 else None,
        volatility_bias=volatility.bias if volatility else None
    )

    return trade_score, inv_score


def get_price_at_date(ticker: str, target_date: datetime, db: Database) -> Optional[float]:
    """
    Get closing price on a specific date (or nearest prior trading day).

    Args:
        ticker: Stock ticker symbol
        target_date: Target date
        db: Database connection

    Returns:
        Closing price or None if not found
    """
    with db.get_connection() as conn:
        # Get price on or before target date (handles weekends/holidays)
        query = """
            SELECT close
            FROM prices_daily
            WHERE ticker = ?
            AND trade_date <= ?
            ORDER BY trade_date DESC
            LIMIT 1
        """
        cursor = conn.execute(query, (ticker, target_date.strftime('%Y-%m-%d')))
        row = cursor.fetchone()
        return row[0] if row else None


def calculate_forward_return(
    ticker: str,
    from_date: datetime,
    from_price: float,
    days_forward: int,
    db: Database
) -> Optional[float]:
    """
    Calculate percentage return from a date to N days in the future.

    Args:
        ticker: Stock ticker symbol
        from_date: Starting date
        from_price: Starting price
        days_forward: Number of days to look forward
        db: Database connection

    Returns:
        Percentage return (e.g., 0.053 = 5.3%) or None if no data
    """
    target_date = from_date + timedelta(days=days_forward)
    to_price = get_price_at_date(ticker, target_date, db)

    if to_price is None or from_price == 0:
        return None

    return (to_price - from_price) / from_price


def backtest_ticker(
    ticker: str,
    db: Database,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    interval_days: int = 7
) -> List[BacktestResult]:
    """
    Back-test Iceberg Scores for a ticker over a date range.

    Args:
        ticker: Stock ticker symbol
        db: Database connection
        start_date: Start date (default: 6 months ago)
        end_date: End date (default: today)
        interval_days: Days between test points (default: 7 = weekly)

    Returns:
        List of BacktestResult objects
    """
    # Default date range: past 6 months
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=180)

    results = []
    current_date = start_date

    while current_date <= end_date:
        # Calculate scores as of this date
        scores = calculate_score_at_date(ticker, current_date, db)

        if scores:
            trade_score, inv_score = scores
            price = get_price_at_date(ticker, current_date, db)

            if price:
                # Calculate forward returns
                return_2w = calculate_forward_return(ticker, current_date, price, 14, db)
                return_1m = calculate_forward_return(ticker, current_date, price, 30, db)
                return_3m = calculate_forward_return(ticker, current_date, price, 90, db)

                result = BacktestResult(
                    date=current_date.strftime('%Y-%m-%d'),
                    price=price,
                    trade_score=trade_score,
                    investment_score=inv_score,
                    trade_rating=get_rating_label(trade_score),
                    investment_rating=get_rating_label(inv_score),
                    return_2w=return_2w,
                    return_1m=return_1m,
                    return_3m=return_3m
                )
                results.append(result)

        # Move to next interval
        current_date += timedelta(days=interval_days)

    return results


def evaluate_accuracy(
    results: List[BacktestResult],
    score_type: str = 'trade'
) -> Dict[str, AccuracyStats]:
    """
    Evaluate accuracy of ratings by measuring forward returns.

    Args:
        results: List of BacktestResult objects
        score_type: 'trade' or 'investment'

    Returns:
        Dictionary mapping rating to AccuracyStats
    """
    # Group results by rating
    by_rating = defaultdict(list)
    for r in results:
        rating = r.trade_rating if score_type == 'trade' else r.investment_rating
        by_rating[rating].append(r)

    # Calculate stats for each rating tier
    stats = {}
    for rating, results_list in by_rating.items():
        # Filter out None returns for each timeframe
        returns_2w = [r.return_2w for r in results_list if r.return_2w is not None]
        returns_1m = [r.return_1m for r in results_list if r.return_1m is not None]
        returns_3m = [r.return_3m for r in results_list if r.return_3m is not None]

        # Calculate statistics
        positive_rate_2w = sum(1 for r in returns_2w if r > 0) / len(returns_2w) if returns_2w else 0
        avg_return_2w = sum(returns_2w) / len(returns_2w) if returns_2w else 0

        positive_rate_1m = sum(1 for r in returns_1m if r > 0) / len(returns_1m) if returns_1m else 0
        avg_return_1m = sum(returns_1m) / len(returns_1m) if returns_1m else 0

        positive_rate_3m = sum(1 for r in returns_3m if r > 0) / len(returns_3m) if returns_3m else 0
        avg_return_3m = sum(returns_3m) / len(returns_3m) if returns_3m else 0

        stats[rating] = AccuracyStats(
            rating=rating,
            count=len(results_list),
            positive_rate_2w=positive_rate_2w,
            avg_return_2w=avg_return_2w,
            positive_rate_1m=positive_rate_1m,
            avg_return_1m=avg_return_1m,
            positive_rate_3m=positive_rate_3m,
            avg_return_3m=avg_return_3m
        )

    return stats


def print_backtest_report(
    ticker: str,
    results: List[BacktestResult],
    start_date: datetime,
    end_date: datetime
):
    """
    Print formatted back-test report to console.

    Args:
        ticker: Stock ticker symbol
        results: List of BacktestResult objects
        start_date: Test period start date
        end_date: Test period end date
    """
    if not results:
        print(f"\n{ticker} Back-Test: No data available\n")
        return

    print(f"\n{'='*70}")
    print(f"{ticker} Back-Test Report")
    print(f"{'='*70}")
    print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Test Points: {len(results)} (weekly intervals)")
    print(f"{'='*70}\n")

    # Evaluate both score types
    for score_type, label in [('trade', 'Trade Score'), ('investment', 'Investment Score')]:
        print(f"\n{label} Analysis")
        print(f"{'-'*70}")

        stats = evaluate_accuracy(results, score_type)

        # Print stats in order from best to worst rating
        rating_order = ['STRONG BUY', 'BUY', 'OUTPERFORM', 'HOLD', 'UNDERPERFORM', 'SELL']

        print(f"\n{'Rating':<15} {'Count':<8} {'2-Week':<20} {'1-Month':<20} {'3-Month':<20}")
        print(f"{'-'*70}")

        for rating in rating_order:
            if rating in stats:
                s = stats[rating]

                # Format: "75.0% (+4.2%)"
                def format_result(pos_rate, avg_return):
                    sign = '+' if avg_return >= 0 else ''
                    return f"{pos_rate*100:>4.1f}% ({sign}{avg_return*100:>5.1f}%)"

                print(f"{rating:<15} {s.count:<8} "
                      f"{format_result(s.positive_rate_2w, s.avg_return_2w):<20} "
                      f"{format_result(s.positive_rate_1m, s.avg_return_1m):<20} "
                      f"{format_result(s.positive_rate_3m, s.avg_return_3m):<20}")

    # Overall summary
    print(f"\n{'='*70}")
    print(f"Summary Statistics")
    print(f"{'-'*70}")

    # Calculate overall returns
    all_returns_2w = [r.return_2w for r in results if r.return_2w is not None]
    all_returns_1m = [r.return_1m for r in results if r.return_1m is not None]
    all_returns_3m = [r.return_3m for r in results if r.return_3m is not None]

    avg_2w = sum(all_returns_2w) / len(all_returns_2w) if all_returns_2w else 0
    avg_1m = sum(all_returns_1m) / len(all_returns_1m) if all_returns_1m else 0
    avg_3m = sum(all_returns_3m) / len(all_returns_3m) if all_returns_3m else 0

    print(f"Average 2-Week Return:  {avg_2w*100:+6.2f}%")
    print(f"Average 1-Month Return: {avg_1m*100:+6.2f}%")
    print(f"Average 3-Month Return: {avg_3m*100:+6.2f}%")

    # Best and worst calls
    if all_returns_3m:
        best_idx = max(range(len(results)), key=lambda i: results[i].return_3m or -999)
        worst_idx = min(range(len(results)), key=lambda i: results[i].return_3m or 999)

        best = results[best_idx]
        worst = results[worst_idx]

        print(f"\nBest Call (3-month):")
        print(f"  Date: {best.date}, Price: ${best.price:.2f}")
        print(f"  Trade: {best.trade_rating} ({best.trade_score}), Investment: {best.investment_rating} ({best.investment_score})")
        print(f"  3-Month Return: {best.return_3m*100:+.2f}%")

        print(f"\nWorst Call (3-month):")
        print(f"  Date: {worst.date}, Price: ${worst.price:.2f}")
        print(f"  Trade: {worst.trade_rating} ({worst.trade_score}), Investment: {worst.investment_rating} ({worst.investment_score})")
        print(f"  3-Month Return: {worst.return_3m*100:+.2f}%")

    print(f"\n{'='*70}\n")


def run_backtest(ticker: str, months: int = 6):
    """
    Run back-test for a ticker and print report.

    Args:
        ticker: Stock ticker symbol
        months: Number of months to test (default: 6)
    """
    # Load database
    from ..config import Config
    config = Config.load()
    db = Database(config.db_path)

    # Set date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)

    print(f"\nRunning back-test for {ticker}...")
    print(f"Calculating scores at weekly intervals...")

    # Run back-test
    results = backtest_ticker(ticker, db, start_date, end_date, interval_days=7)

    # Print report
    print_backtest_report(ticker, results, start_date, end_date)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("\nUsage: python -m iceberg.analysis.backtest TICKER [MONTHS]")
        print("\nExamples:")
        print("  python -m iceberg.analysis.backtest RKLB")
        print("  python -m iceberg.analysis.backtest MU 12")
        print("\nDefaults to 6 months of history.\n")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    months = int(sys.argv[2]) if len(sys.argv) > 2 else 6

    run_backtest(ticker, months)
