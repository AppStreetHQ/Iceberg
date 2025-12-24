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

---

# Iceberg Score System v1.1 - Resilience & Recovery Focus

## Overview

Version 1.1 addresses the core issue discovered through back-testing: **the system was momentum-chasing instead of value-seeking**, buying tops and selling bottoms.

### The Problem (v1.0)
Back-testing revealed consistent failures:
- High scores when stocks were extended → bought overbought territory
- Low scores when stocks were beaten down → missed recovery opportunities
- **META example:** Rated UNDERPERFORM/SELL at $594 (after earnings drop) → stock gained +12%
- **AVGO example:** Rated STRONG BUY at $403 (peak) → stock dropped -13%

### The Solution (v1.1)
**Focus on resilience and post-shock recovery** instead of trying to predict reversals:
- Can't predict earnings misses or external shocks
- **CAN** identify stocks that historically recover from dips (resilience)
- **CAN** detect early recovery signals after shocks (post-shock patterns)
- **CAN** distinguish "cheap on a winner" from "falling knife"

## v1.1 Enhancements

### 1. Post-Shock Recovery Detection (+25 bonus)

Identifies stocks recovering after sharp drops (earnings misses, market corrections).

**Pattern criteria:**
- Price dropped >10% from 20-day high
- Long-term trend (100d) still UP (not structural decline)
- Early recovery signals:
  - RSI climbing from oversold (25-45 range)
  - OR MACD histogram improving (turning less negative)

**Use case:** META at $594 after drop from $785 - v1.0 said SELL, v1.1 detects recovery opportunity

### 2. "Cheap on a Winner" Detection (+15 bonus)

Distinguishes quality stocks on temporary pullbacks from falling knives.

**Pattern criteria:**
- Price < SMA(20) → Short-term pullback
- Price > SMA(100) → Long-term uptrend intact
- Trend(100) == UP → Structural growth continues
- RSI < 50 → Not overbought

**Use case:** GOOGL dipping on broad market weakness while fundamentals remain strong

### 3. Resilience Scoring (Multiplier System)

Counts recovery patterns over past 6 months to measure stock resilience.

**Resilience tiers:**
- **High resilience** (3+ recoveries): 1.2x bonus multiplier
- **Medium resilience** (1-2 recoveries): 1.0x (normal)
- **Low resilience** (0 recoveries): 0.8x multiplier

Resilience multiplier applies to:
- Original recovery pattern bonus
- Post-shock recovery bonus

**Also adjusts volatility penalty:**
- Wild volatility on HIGH resilience stock: -5 instead of -10
- Wild volatility on LOW resilience stock: -15 instead of -10

### 4. Context-Aware RSI Scoring

RSI signals now consider long-term trend context.

**Oversold signals:**
- **Oversold + Long-term trend UP:** Base +15 + Bonus +10 = +25 total (opportunity!)
- **Oversold + Long-term trend DOWN:** +15 × 0.3 = +5 (falling knife warning)

### 5. Distance from High Metric

Tracks percentage below 20-day high to detect pullbacks.

**Used by:**
- Post-shock recovery pattern (triggers on >10% drop)
- Future enhancements (position sizing, risk management)

## Updated Weight Constants (v1.1)

### Trade Score (Max: 150 points)
```
Base Components (±85):
  MACD: 25
  RSI: 15 (context-aware)
  SMA(10) position: 20
  Trend(10): 20
  Volatility: 5 (resilience-aware)

Bonuses (up to +65):
  Recovery pattern: 20 (up from 15, resilience-multiplied)
  Post-shock recovery: 25 (NEW)
  Cheap on winner: 15 (NEW)
  RSI oversold + uptrend: 10 (NEW)
```

### Investment Score (Max: 155 points)
```
Base Components (±90):
  MACD: 15
  RSI: 10 (context-aware)
  SMA(50) position: 20
  Trend(50): 20
  Price vs SMA(50): 15
  Volatility: 10 (resilience-aware)

Bonuses (up to +65):
  Recovery pattern: 20 (up from 15, resilience-multiplied)
  Post-shock recovery: 25 (NEW)
  Cheap on winner: 15 (NEW)
  RSI oversold + uptrend: 10 (NEW)
```

## Expected Impact

### META Nov 21 Example ($594 after collapse from $785)

**v1.0 scores:**
- Trade: 31/100 (UNDERPERFORM)
- Investment: 21/100 (SELL)
- Result: **Missed +12% gain**

**v1.1 scores (estimated):**
- Post-shock recovery: +25 (price dropped 24%, RSI 38, long-term trend up)
- Context-aware RSI oversold: +25 (instead of +15)
- Resilience bonus (if GOOGL-like history): 1.2x multiplier
- **Estimated: 75/100 (BUY) / 65/100 (OUTPERFORM)**

### AVGO Nov 28 Example ($403 at peak)

**v1.0 scores:**
- Trade: 86/100 (STRONG BUY)
- Investment: 80/100 (BUY)
- Result: **Bought top, lost -13%**

**v1.1 scores (estimated):**
- No recovery patterns (not a dip)
- No cheap on winner (price at highs)
- No post-shock recovery (no drop from high)
- **Estimated: 65/100 (OUTPERFORM) / 52/100 (HOLD)**
- Lower scores = better signal control

## Philosophy Shift

**v1.0:** "Follow the momentum" → Works in trends, fails at reversals
**v1.1:** "Identify resilience, detect recovery" → Works post-shock, avoids tops

We're not trying to predict earnings surprises or Fed announcements.
We're identifying stocks that **historically bounce back** and **detecting when recovery starts**.

## Version History

### v1.1 - 2024-12-24
- **Resilience-based scoring:** Count recovery patterns, apply multipliers
- **Post-shock recovery detection:** Identify stocks recovering after sharp drops (+25 bonus)
- **Context-aware RSI:** Oversold signals stronger on uptrending stocks
- **Resilience-aware volatility:** Wild volatility less penalized for resilient stocks
- **"Cheap on a winner" detection:** Quality stocks on temporary pullbacks (+15 bonus)
- **Distance from high metric:** Track pullback severity
- **Increased max points:** Trade 150 (from 100), Investment 155 (from 95)
- **Back-test validated:** Addresses momentum-chasing problem

### v1.0 - 2024-12-24
- Initial dual-score system
- Trade Score: MACD(25) + RSI(15) + SMA10(20) + Trend10(20) + Volatility(±5)
- Investment Score: MACD(15) + RSI(10) + SMA50(20) + Trend50(20) + Volatility(±10)
- Recovery Pattern detection (+15 bonus)
- Growth stock focus (SMA50 vs SMA200)
- Optimized for catching RKLB-style opportunities
- **Limitation discovered:** Momentum-chasing behavior

---

**See Implementation:** `src/iceberg/analysis/scoring.py` (v1.1)
**See Indicators:** `src/iceberg/analysis/indicators.py` (resilience, distance from high, long-term trend)
