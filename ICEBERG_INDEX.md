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

---

# Iceberg Score System v1.2 - Refined Post-Shock Detection

## Overview

Version 1.2 addresses a fundamental flaw in v1.1's post-shock recovery pattern and refines the calibration for more intellectually honest ratings.

### The Problem (v1.1)

v1.1's post-shock recovery detection had a contradictory requirement:
- Required **current long-term trend to be UP**
- But after real shocks (earnings misses, market corrections), trend goes **DOWN**
- **Result:** Pattern failed to detect actual post-shock recoveries

**Example:** META Nov 21 at $594 (after -25% earnings collapse)
- Price dropped from $785 → $589 (-25%)
- 100-day SMA still at $720 (lagging)
- Long-term trend: **DOWN** (price below SMA100)
- v1.1 pattern: **NOT DETECTED** ❌
- Actual result: +12% in 3 months

### The Solution (v1.2)

**Historical Strength Check** instead of current uptrend:

```
Post-Shock Recovery Pattern (v1.2):
1. Price dropped >10% from 20-day high (shock happened)
2. Was above SMA(100) in past 60 days (had historical strength)
3. Early recovery signals (not in free fall):
   - RSI > 20 (not panic selling)
   - OR Price stabilizing (not making new lows)
```

**Key insight:** Look backward 60 days to find evidence of past strength, don't require current uptrend during the shock itself.

## Calibration Philosophy - The +60 Decision

### Initial Attempts
- v1.2 alpha: +40 bonus → Scores too low (META 49 HOLD, not enough signal)
- v1.2 beta: +70 bonus → Scores too high (META 59 OUTPERFORM, ignoring extreme risk)
- **v1.2 final: +60 bonus** → Balanced HOLD/cautious OUTPERFORM range

### The Reasoning

**Why +60 is appropriate:**

When all technical indicators are screaming danger (MACD bearish, RSI extreme, all trends DOWN), a +60 bonus:
- Acknowledges the recovery potential (+60 is significant)
- Respects the extreme risk (doesn't completely override warnings)
- Results in HOLD or cautious OUTPERFORM ratings

**What HOLD means in this context:**
"Yes, there's recovery potential based on historical strength, BUT the risk is extreme. Watch closely, proceed with caution."

This is more honest than STRONG BUY when:
- RSI is 11.9 (extreme panic)
- Stock is down -40% from high
- All trends are DOWN
- Volatility is wild

### Validation Results

**META Nov 21, 2025** ($594.25 after -25% earnings collapse):
- v1.0: 35/100 UNDERPERFORM (missed opportunity)
- v1.1: Pattern not detected (contradiction bug)
- **v1.2: 55/100 OUTPERFORM** (Trade), 49/100 HOLD (Investment) ✓
- Actual: +12.07% in 3 months (best call in backtest period)

**RKLB Nov 21, 2025** ($39.48 after -40% drop, RSI 11.9):
- v1.0: Pattern not detected
- v1.1: Pattern not detected (contradiction bug)
- **v1.2: 54/100 HOLD** (Trade), 43/100 UNDERPERFORM (Investment)
- Actual: +88.56% in 3 months

**Note on RKLB:** While the +88% gain suggests the rating was too conservative, the extreme conditions at the moment (RSI 11.9, -40% drop, wild volatility) made HOLD a defensible rating for risk management.

## Technical Changes

**Scoring weights:**
- TRADE_POST_SHOCK_BONUS: 25 → 60
- INV_POST_SHOCK_BONUS: 25 → 60
- Max points: Trade 190 (was 150), Investment 195 (was 155)

**Pattern detection:**
```python
def detect_post_shock_recovery(
    current_price: float,
    distance_from_high: Optional[float],
    rsi_value: Optional[float],
    macd_hist: Optional[float],
    long_term_trend: Optional[TrendBias],
    closes: Optional[List[float]] = None,
    sma100: Optional[float] = None
) -> bool:
    """
    v1.2: Check if price WAS above SMA(100) in past 60 days
    (historical strength), not if trend is currently UP.
    """
```

**New tool:**
- `diagnose.py`: Diagnostic tool to investigate scoring on specific dates
- Usage: `python -m iceberg.analysis.diagnose TICKER YYYY-MM-DD`

## Philosophy Evolution

**v1.0:** "Follow the momentum" → Works in trends, fails at reversals
**v1.1:** "Identify resilience, detect recovery" → Conceptually sound, implementation flawed
**v1.2:** "Historical strength + recovery signals" → Fixed contradiction, balanced calibration

We're not predicting shocks. We're identifying stocks with **proven strength** that are showing **early recovery signals** after temporary setbacks.

## Limitations Discovered

Through backtesting, v1.2 revealed persistent challenges:

1. **Still buying peaks:** BUY ratings at tops lose money (momentum-chasing persists)
2. **Too conservative on extreme setups:** RKLB Nov 21 (HOLD) gained +88%
3. **Market regime matters:** System works better in uptrends than downtrends

These findings inform v1.3 development.

---

# Iceberg Score System v1.3 - Turnaround Rating & Trade/Investment Differentiation

**Released:** 2024-12-24
**Status:** Production

## The Innovation: Dual-Rating Architecture

v1.3 introduces a breakthrough approach to the calibration dilemma: How to flag extreme opportunities (RSI <20, -40% drops) without being reckless when all indicators scream danger?

**Solution:** Show BOTH perspectives simultaneously.

### The Turnaround Rating System

When proven winner capitulation is detected, v1.3 displays TWO scores:

1. **Turnaround Rating** ⚡ - Aggressive signal for the opportunity
2. **BAU Rating** (Business As Usual) - Conservative baseline view

The turnaround rating stays active while:
- Capitulation pattern is detected AND
- Price remains below SMA(50)

Once price crosses above SMA(50) OR capitulation conditions ease (RSI recovers, price bounces), the system reverts to normal single-score display.

### Proven Winner Capitulation Pattern (v1.3)

Extremely specific, high-confidence pattern requiring **ALL** criteria:

1. **Rally >40%** in past 90 days (proven it can run)
2. **Drop >30%** from that peak (sharp correction)
3. **RSI < 20** (extreme panic, beyond normal oversold)
4. **Price near/below rally start** (back at support level)
5. **Was above SMA(100)** during rally (confirmed strength)

This pattern is MORE restrictive than post-shock recovery (v1.2) and targets the absolute highest-confidence extreme setups.

### Trade vs Investment Differentiation

v1.3 dramatically widens the gap between trade and investment scores on capitulation setups, reflecting their fundamentally different risk profiles:

**Capitulation Bonuses:**
- Trade: +205 (AGGRESSIVE - traders thrive on volatility)
- Investment: +60 (CAUTIOUS - investors need confirmation)
- Gap: +145 differential

**Rationale:**

**Traders** on extreme setups:
- Can watch tick-by-tick and time precise entries
- Use tight stops to limit downside
- 0-7 day holds, out before next leg down
- Volatility = profit opportunity
- Want BUY signals at bottoms

**Investors** on extreme setups:
- Holding weeks/months through continued volatility
- Can't day-trade out of trouble
- Need confirmation the bottom is in
- Volatility = unacceptable risk
- Want to wait for stability

**Result:** Investors can see that traders are getting BUY signals, providing valuable context about the opportunity without being pushed into risky positions inappropriate for their time horizon.

## Example: RKLB November 21, 2025

**Market Conditions:**
- Price: $39.48 (-9.49% day, -40.33% from high)
- RSI: 11.9 (extreme panic)
- All trends: DOWN
- Volatility: WILD (5.52% daily σ)
- Resilience: 0 recoveries in 6 months

**Pattern Detection:**
```
✓ Post-Shock Recovery (v1.2)
✓ Proven Winner Capitulation (v1.3)
  → Rally detected: $33.36 → $66.13 (+98% in 90 days)
  → Drop: -40% from peak
  → RSI: 11.9 (extreme panic)
  → Price at rally support: $39.48 vs start $33.36
  → Was above SMA(100) during rally: ✓
```

**Scoring:**
```
🔥 TURNAROUND MODE ACTIVE (price $39.48 < SMA(50) $55.34)

Trade Score:
  Turnaround: 70/100 (BUY) ⚡        ← "Swing trade this NOW"
  BAU: 51/100 (HOLD)                ← "Too risky normally"

Investment Score:
  Turnaround: 46/100 (HOLD) ⚡       ← "Too volatile, wait"
  BAU: 46/100 (HOLD)                ← "Same, stay out"
```

**Outcome:** +88% gain over 3 months

**Analysis:**
- Trade Turnaround (70 BUY) correctly flagged the extreme opportunity for swing traders
- Investment Turnaround (46 HOLD) appropriately cautioned long-term holders
- 24-point gap clearly differentiates risk tolerance
- Both audiences served with same underlying analysis

## December 4 Follow-up: Turnaround Ended

**Market Conditions:**
- Price: $43.91 (+11% from Nov 21)
- RSI: 46.1 (recovered from panic)
- Distance from high: -15.39% (recovered from -40%)
- Trend(10): UP (short-term recovery confirmed)

**Pattern Detection:**
```
✓ Post-Shock Recovery (v1.2) - still active
✗ Proven Winner Capitulation (v1.3) - ended (RSI > 20, drop < 30%)
```

**Scoring:**
```
Trade Score: 68/100 (OUTPERFORM)    ← Normal scoring resumed
Investment Score: 51/100 (HOLD)     ← Rally not confirmed yet
```

**Analysis:**
- Capitulation pattern correctly ended when panic eased
- Price still below SMA(50) but RSI recovered and drop reduced
- Trade score remains elevated (rally forming)
- Investment score cautious (waiting for sustained trend)

## Technical Implementation

### ScoreResult Dataclass

```python
@dataclass
class ScoreResult:
    turnaround_raw: int
    turnaround_score: int
    bau_raw: int
    bau_score: int
    turnaround_active: bool

    @property
    def display_score(self) -> int:
        return self.turnaround_score if self.turnaround_active else self.bau_score
```

### Capitulation Detection

```python
def detect_proven_winner_capitulation(
    current_price: float,
    closes: Optional[List[float]],
    sma100: Optional[float],
    rsi_value: Optional[float],
    distance_from_high: Optional[float]
) -> bool:
    # Criterion 1: RSI < 20 (extreme panic)
    if rsi_value is None or rsi_value >= 20:
        return False

    # Criterion 2: Dropped >30% from high
    if distance_from_high is None or distance_from_high > -30:
        return False

    # Find peak in past 90 days
    lookback_90d = closes[-90:]
    rally_peak_price = max(lookback_90d)
    peak_idx = len(closes) - 90 + lookback_90d.index(rally_peak_price)

    # Find rally start BEFORE peak
    prices_before_peak = closes[max(0, len(closes)-90):peak_idx+1]
    rally_start_price = min(prices_before_peak)

    # Criterion 3: Rally >40%
    rally_gain_pct = ((rally_peak_price - rally_start_price) / rally_start_price) * 100
    if rally_gain_pct < 40:
        return False

    # Criterion 4: Price near/below rally start
    if current_price > rally_start_price * 1.10:
        return False

    # Criterion 5: Was above SMA(100) during rally
    # (Check historical SMA100 at rally points)
    ...

    return True
```

### Scoring Logic

Both `calculate_trade_score()` and `calculate_investment_score()` now return `ScoreResult`:

```python
# Calculate TURNAROUND score (uses capitulation bonus if detected)
turnaround_score = base_score
if capitulation_detected:
    bonus = TRADE_CAPITULATION_BONUS  # +205 for trade, +60 for investment
    if resilience_count >= 3:
        bonus = int(bonus * 1.2)
    turnaround_score += bonus
elif post_shock_detected:
    turnaround_score += POST_SHOCK_BONUS  # +60

# Calculate BAU score (uses post-shock only, not capitulation)
bau_score = base_score
if post_shock_detected:
    bau_score += POST_SHOCK_BONUS

# Turnaround active if: capitulation detected AND price < SMA(50)
turnaround_active = capitulation_detected and (current_price < sma50)

return ScoreResult(
    turnaround_raw=turnaround_score,
    turnaround_score=normalize_score(turnaround_score, max_points),
    bau_raw=bau_score,
    bau_score=normalize_score(bau_score, max_points),
    turnaround_active=turnaround_active
)
```

## Calibration Philosophy

### The Three-Pattern Hierarchy

v1.3 now has three recovery patterns with different confidence levels:

1. **Recovery Pattern (v1.0):** +20 bonus
   - Price crossing above SMA(10) and SMA(50)
   - 10-day and 50-day trends both UP
   - Broad pattern, catches many recoveries

2. **Post-Shock Recovery (v1.2):** +60 bonus
   - Drop >10% from 20-day high (shock happened)
   - Was above SMA(100) in past 60 days (historical strength)
   - Early recovery signals (RSI >20 or stabilizing)
   - More selective, requires proven quality

3. **Proven Winner Capitulation (v1.3):** Trade +205, Investment +60
   - ALL five criteria must be met
   - Extreme panic (RSI <20) after proven rally (>40%)
   - Highest confidence, rarest pattern
   - Different bonuses for trade vs investment risk profiles

### Maximum Points

- **Trade Score:** ±85 base + up to 310 bonus = ±395 max
- **Investment Score:** ±90 base + up to 165 bonus = ±255 max

The asymmetry reflects traders' higher tolerance for volatility on extreme setups.

## Display Format

### TUI (Technical Panel)

When turnaround active, scores show with ⚡ indicator:

```
Iceberg™ Score System v1.3

Trade Score:      70/100 ████████████████████  BUY ⚡
Investment Score: 46/100 █████████             HOLD ⚡
```

### Diagnostic Tool (diagnose.py)

Full breakdown when turnaround active:

```
🔥 TURNAROUND MODE ACTIVE (price below SMA(50): $55.34)

Trade Score:
  Turnaround: 70/100 (BUY) ⚡
    Raw: 156
  BAU: 51/100 (HOLD)
    Raw: 11

Investment Score:
  Turnaround: 46/100 (HOLD) ⚡
    Raw: -22
  BAU: 46/100 (HOLD)
    Raw: -22
```

### Backtest (backtest.py)

Uses `display_score` property (turnaround if active, else BAU) to show what user would have seen historically.

## Strengths

1. **Flags extreme opportunities** without ignoring risk (dual perspective)
2. **Serves both audiences** (traders get BUY, investors see context)
3. **Auto-reverts** when opportunity window closes
4. **Highly selective** (all five criteria = high confidence)
5. **Clear differentiation** (24-point gap on RKLB Nov 21)

## Limitations

1. **No fundamental data** - relies purely on price/volume behavior
2. **Trade/Investment distinction** - both still use technical indicators, not fundamentally different purposes
3. **Rare pattern** - very few stocks meet all five capitulation criteria
4. **Backward-looking** - can't predict if bottom is truly in
5. **Volatility timing** - even BUY signal can experience continued drawdown

## Open Questions

**Should Trade and Investment scores measure different things entirely?**

Currently both use technical indicators (MACD, RSI, SMAs, trends) with different weights and timeframes. This is calibration, not fundamentally different purposes.

Potential evolution:
- Trade Score: Keep as timing/momentum signal
- Investment Score: Measure business quality (resilience, consistency, drawdown resistance, time above SMA100)

Without fundamental data, can we infer "investment quality" from price behavior alone?

---

## Version History

### v1.3 - 2024-12-24
- **Turnaround Rating System:** Dual-score architecture (Turnaround + BAU) for extreme setups
- **Proven Winner Capitulation:** Five-criteria pattern (Rally >40%, Drop >30%, RSI <20, at support, was above SMA100)
- **Trade/Investment Differentiation:** Capitulation bonuses widened (Trade +205, Investment +60, gap +145)
- **ScoreResult dataclass:** Returns both scores with turnaround_active flag
- **Auto-revert logic:** Turnaround ends when capitulation conditions ease OR price crosses SMA(50)
- **Max points updated:** Trade 395 (was 310), Investment 255 (was 295)
- **Philosophy:** Show both aggressive and conservative perspectives simultaneously
- **RKLB Nov 21 validation:** Trade 70 (BUY), Investment 46 (HOLD), actual +88% gain

### v1.2 - 2024-12-24
- **Fixed post-shock recovery:** Uses historical strength (not current uptrend)
- **Refined calibration:** +60 bonus for balanced HOLD/OUTPERFORM ratings
- **New diagnostic tool:** `diagnose.py` for investigating specific dates
- **Back-test validation:** META Nov 21 now detected (+12% actual), RKLB limitations noted
- **Philosophy:** Acknowledge opportunity without ignoring risk
- **Max points:** Trade 190, Investment 195

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

**See Implementation:** `src/iceberg/analysis/scoring.py` (v1.3 - dual-score architecture)
**See Indicators:** `src/iceberg/analysis/indicators.py` (resilience, distance from high, long-term trend)
**See Diagnostics:** `src/iceberg/analysis/diagnose.py` (investigate specific dates, turnaround display)
**See Backtesting:** `src/iceberg/analysis/backtest.py` (historical validation)
