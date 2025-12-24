# Iceberg Score System

## Overview

The Iceberg Score is a proprietary dual-score system designed to evaluate stocks from two distinct perspectives:

- **Trade Score (0-100):** Short-term momentum and entry timing for swing traders
- **Investment Score (0-100):** Long-term trend and value assessment for position holders

Both scores use weighted technical indicators but emphasize different timeframes and metrics.

## Philosophy

Traditional technical analysis shows individual indicators, but traders need actionable signals. The Iceberg Score synthesizes multiple metrics into clear, numeric scores that answer:

- **Trade Score:** "Should I enter a position NOW?"
- **Investment Score:** "Is this a quality opportunity for long-term holding?"

### Why Dual Scores?

Different strategies require different signals:
- A high-momentum stock (MU) might score **Trade: 85 / Investment: 58** → Great swing trade, risky hold
- A stable grower on sale might score **Trade: 52 / Investment: 78** → Patient buy, not urgent
- A perfect setup (NVDA bull run) scores **Trade: 90 / Investment: 88** → Strong buy, any timeframe

## Scoring Components

### Trade Score Weights (Total: ±85 points)

| Component | Weight | Purpose |
|-----------|--------|---------|
| MACD | 25 | Momentum shifts (bull/bear/neutral) |
| RSI | 15 | Strength and oversold opportunities |
| SMA(10) Position | 20 | Immediate trend (is it bouncing NOW?) |
| Trend(10) | 20 | Recovery confirmation |
| Volatility | ±5 | Wild = opportunity (+5), Calm = stable (+5) |
| Recovery Pattern | +15 | Bonus for detected bounce patterns |

**Max Raw Score:** ±100 (with bonus)

### Investment Score Weights (Total: ±80 points)

| Component | Weight | Purpose |
|-----------|--------|---------|
| MACD | 15 | Momentum alignment |
| RSI | 10 | Strength confirmation |
| SMA(50) Position | 20 | Recent growth baseline (not 200d - optimized for growth stocks) |
| Trend(50) | 20 | Medium-term trend intact? |
| Price vs SMA(50) | 15 | Distance from "normal" level |
| Volatility | ±10 | Wild = risk (-10), Calm = stability (+10) |
| Recovery Pattern | +15 | Bonus for quality dips |

**Max Raw Score:** ±95 (with bonus)

## Component Scoring Details

### MACD (Moving Average Convergence Divergence)
- **Bull** (Histogram > 0): Trade +25, Investment +15
- **Neutral** (Histogram ≈ 0): Trade 0, Investment 0
- **Bear** (Histogram < 0): Trade -25, Investment -15

### RSI (Relative Strength Index, 14-period)
- **Oversold** (<30): Trade +15, Investment +15 (buying opportunity)
- **Weak** (30-40): Trade -10, Investment -10
- **Neutral** (40-60): Trade 0, Investment 0
- **Strong** (60-70): Trade +10, Investment +10
- **Overbought** (>70): Trade -15, Investment -15 (sell signal)

### SMA Position
Measures price distance from moving average, capped at weight limit.

**Trade Score - SMA(10):**
```
Score = (Price - SMA(10)) / SMA(10) × 100
Capped at: ±20 points
```

**Investment Score - SMA(50):**
```
Score = (Price - SMA(50)) / SMA(50) × 100
Capped at: ±20 points
```

### Trend Direction
Compares current price to SMA (same period as above).

**Trade - Trend(10):**
- Up (>+2% above SMA): +20
- Sideways (-2% to +2%): 0
- Down (<-2% below SMA): -20

**Investment - Trend(50):**
- Up (>+2% above SMA): +20
- Sideways (-2% to +2%): 0
- Down (<-2% below SMA): -20

### Volatility
Daily standard deviation of returns.

**Trade Score:**
- Calm (<1%): +5 (stable entry)
- Choppy (1-3%): 0
- Wild (>3%): +5 (opportunity in volatility)

**Investment Score:**
- Calm (<1%): +10 (low risk)
- Choppy (1-3%): 0
- Wild (>3%): -10 (high risk)

### Recovery Pattern Bonus

Detects stocks bouncing from temporary pullbacks - the "buy the dip" opportunity.

**Pattern Detection:**
```
If ALL of these are true:
  - Price < SMA(50)     (below recent high - pullback happened)
  - Price > SMA(10)     (above immediate low - recovery starting)
  - Trend(10) == Up     (momentum turning positive)
  - Trend(50) == Up     (long-term growth still intact)

Then:
  Trade Score: +15
  Investment Score: +15
```

**Use Case:** High-growth stocks (RKLB, NVDA) that have temporary setbacks but fundamentals remain strong. Catches multiple re-entry opportunities as the stock oscillates.

## Score Normalization

Raw scores are normalized to 0-100 scale for consistency.

**Formula:**
```
Score = ((RawScore + MaxPoints) / (MaxPoints × 2)) × 100
```

**Trade Score:**
```
Score = ((RawScore + 100) / 200) × 100
```

**Investment Score:**
```
Score = ((RawScore + 95) / 190) × 100
```

## Categorical Ratings

Scores map to traditional ratings:

| Score Range | Rating |
|-------------|--------|
| 85-100 | STRONG BUY |
| 70-84 | BUY |
| 55-69 | OUTPERFORM |
| 45-54 | HOLD |
| 30-44 | UNDERPERFORM |
| 0-29 | SELL |

## Example Calculations

### RKLB - Growth Stock Recovery

**Scenario:** RKLB rallied from $10 → $77, pulled back to $70, now bouncing.

**Indicators:**
- MACD: Bull (Hist +2.5)
- RSI: 58 (Neutral/Strong boundary)
- Price: $75
- SMA(10): $72 (+4.2% above)
- SMA(50): $65 (+15.4% above)
- Trend(10): Up
- Trend(50): Up
- Volatility: Wild (σ = 3.5%)
- Recovery Pattern: No (price above both SMAs)

**Trade Score:**
```
MACD Bull:        +25
RSI Neutral:      +5
SMA(10) +4.2%:    +4 (capped)
Trend(10) Up:     +20
Volatility Wild:  +5
Recovery Bonus:   0
─────────────────
Raw Score:        +59
Score:            79/100  ████████████████░░░░  BUY
```

**Investment Score:**
```
MACD Bull:        +15
RSI Neutral:      +5
SMA(50) +15.4%:   +15 (capped)
Trend(50) Up:     +20
Volatility Wild:  -10
Recovery Bonus:   0
─────────────────
Raw Score:        +45
Score:            73/100  ██████████████░░░░░░  BUY
```

**Interpretation:** Strong trade setup (momentum + bounce confirmed), solid long-term hold (above growth trend).

## Design Rationale

### Why SMA(50) instead of SMA(200)?

The Investment Score uses **SMA(50)** (≈2.5 months) rather than the traditional SMA(200) (≈10 months) because:

1. **Growth Stock Focus:** High-growth stocks (RKLB, TSLA, NVDA) can rally 300%+ in 6-12 months
2. **Multiple Opportunities:** SMA(200) is too slow to catch pullback re-entries on the same stock
3. **Retail Trading:** Modern traders hold positions for weeks/months, not years
4. **Volatility Era:** 2020s markets move faster than historical norms

SMA(200) works for blue-chips and value stocks. Iceberg targets growth/momentum opportunities.

### Why Different Volatility Weighting?

**Trade Score:** Volatility = opportunity (Wild gets +5)
- Swing traders profit from movement
- Bigger swings = bigger potential gains

**Investment Score:** Volatility = risk (Wild gets -10)
- Position holders want stability
- Wild moves increase drawdown risk

## Future Enhancements

Potential additions being considered:

- **Volume trends:** Increasing volume on rallies = confirmation
- **Rate of change:** Price momentum over N days
- **Support/Resistance:** Distance from key levels
- **Sector correlation:** Relative strength vs sector ETF
- **Customizable profiles:** Growth/Value/Crypto-specific weights

## Version History

### v1.0 - 2024-12-24
- Initial dual-score system
- Trade Score: MACD(25) + RSI(15) + SMA10(20) + Trend10(20) + Volatility(±5)
- Investment Score: MACD(15) + RSI(10) + SMA50(20) + Trend50(20) + Volatility(±10)
- Recovery Pattern detection (+15 bonus)
- Growth stock focus (SMA50 vs SMA200)
- Optimized for catching RKLB-style opportunities

---

**See Implementation:** `src/iceberg/analysis/scoring.py`
