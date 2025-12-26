# Iceberg Scores 2.0 - Independent Dual-Score System

## Overview

Design and implement two independent scoring systems for stock analysis, each serving a distinct purpose and time horizon:

1. **Trade Score** - Short-term entry timing for swing trades (days/weeks)
2. **Investment Score** - Long-term quality assessment for buy-and-hold (months/years)

## Core Principles

### Independence
- **Separate calculations**: Each score has its own independent logic
- **No cross-contamination**: Changing Trade Score won't break Investment Score and vice versa
- **Clear separation of concerns**: Avoid confusion during development and maintenance

### Shared Infrastructure
- **Common indicator functions**: Both scores can use shared technical indicators (MACD, RSI, SMA, etc.)
  - **Important**: When fixing bugs or improving indicator calculations (e.g., fixing compute_macd logic), both scores automatically benefit
  - This does NOT cause confusion because each score uses the metrics independently for its own purpose
  - Example: compute_rsi() is shared, but Trade Score uses it for entry timing while Investment Score uses it for bottom confirmation
- **Same data source**: Both read from the same price history
- **Unified presentation**: Both use the same ScoreResult dataclass and display helpers

### Different Purposes
- **Trade Score**: Identifies good entry points for short-term trades
- **Investment Score**: Identifies quality growth stocks worth holding long-term

## Architecture

### File Structure

```
src/iceberg/analysis/
├── indicators.py          # Shared technical indicator calculations
│   ├── compute_macd()
│   ├── compute_rsi()
│   ├── compute_sma()
│   ├── compute_trend()
│   ├── compute_volatility()
│   ├── compute_growth_rate()
│   ├── compute_rally_magnitude()
│   └── ... (all shared functions)
│
├── scoring.py             # Independent scoring logic
│   ├── ScoreResult        # Shared dataclass
│   ├── calculate_trade_score()      # INDEPENDENT - Trade logic only
│   ├── calculate_investment_score() # INDEPENDENT - Investment logic only
│   ├── get_rating_label() # Shared helper with separate thresholds
│   ├── get_rating_color() # Shared helper
│   └── generate_score_bar() # Shared helper
│
├── backtest.py            # Validation infrastructure (unchanged)
├── diagnose.py            # Debug tool (unchanged)
└── models.py              # Shared data models (unchanged)
```

### Rating Thresholds

**Trade Score** (aggressive - more signals):
- 75-100: STRONG BUY
- 55-74: BUY
- 45-54: HOLD
- 0-44:  AVOID

**Investment Score** (selective - quality only):
- 80-100: STRONG BUY
- 60-79: BUY
- 45-59: HOLD
- 30-44: UNDERPERFORM
- 0-29: SELL

## Trade Score (Short-term Entry Timing)

### Purpose
Identify swing trade opportunities AND signal when short-term upside is exhausted.

**Dual Function:**
1. **Entry signals**: Flag dips, pullbacks, recovery setups
2. **Exit signals**: Drop to HOLD/AVOID when short-term target reached (user then checks Investment Score for long-term hold decision)

### Time Horizon
- Primary: Days to weeks
- Validation: 1-month forward returns

### Focus Areas
1. **Sharp drops on upward-trending stocks** - Buy the dip on quality stocks (e.g., RKLB)
2. **Quick recovery potential** - Stocks that have rebounded quickly before (resilience)
3. **Solid upward trajectories** - Momentum plays on stocks in strong uptrends
4. **Pullbacks from highs** - Entry points when off previous highs but fundamentals intact
5. **New highs / breakouts** - Continued ascent, momentum trades (riskier but valid)

### Two Types of Trade Opportunities

**Type 1: Dip/Recovery Plays** (buy weakness)
- Stock drops sharply but has resilience history
- Near-term recovery to SMA(20) or previous levels expected
- Lower risk, clearer target

**Type 2: Momentum/Breakout Plays** (buy strength)
- Stock in strong uptrend, hitting new highs
- Near-term continued ascent expected
- Higher risk, but growth momentum is real
- Valid trade even if not "sustainable" long-term

Both are valid swing trades - different risk/reward profiles.

### Key Indicators
- **Distance from recent high** - Is it off recent highs? (pullback opportunity)
- **Resilience count** - Historical bounce-back behavior (quick recovery pattern)
- **Sharp drop detection** - Recent large decline (potential dip vs crash)
- **SMA recovery potential** - Below SMA(10)/SMA(20) = bounce opportunity
- **Long-term context** - Was it on upward trend before drop? (TrendBias.UP on longer period)
- **Short-term momentum** - MACD, RSI for entry timing
- **Trend strength** - 10-day and 20-day trends

### Scoring Logic

**Philosophy**: Flag opportunities for further investigation, not definitive signals. Trades carry risk - the score identifies interesting setups worth analyzing.

```
Start at 50 (neutral)

OPPORTUNITY SIGNALS (identify both dip plays AND momentum plays):

Type 1: Dip/Recovery Plays (buy weakness):
+ Sharp drop (-8%+ in 5 days) on stock with long-term uptrend = +20
+ High resilience count (3+ historical recoveries) = +15
+ Pullback from high (-10% to -25% off high) = +10
+ Below SMA(10) or SMA(20) but 50-day trend still up = +15
+ RSI oversold (< 35) = +12

Type 2: Momentum/Breakout Plays (buy strength):
+ Strong 50-day uptrend = +15
+ MACD bullish = +12
+ Above SMA(20) and rising = +10
+ Near highs (within -5%) OR new highs = +10 (momentum trade)
+ Recent strong gain (+10%+ in 10 days) = +8 (near-term growth)

CAUTION FLAGS (light penalties - still flag for review):
- Severe extended drop (> -40% from high) = -15 (might be structural)
- Long-term downtrend (50-day) = -10 (weaker setup)
- Very extended rally (> +40% in 10 days) = -8 (might be overheating)
```

**Design Notes**:
- Identifies TWO types of opportunities: dip/recovery AND momentum/breakout
- Dip plays stack bonuses (drop + resilience + recovery = STRONG BUY)
- Momentum plays stack bonuses (trend + MACD + near highs = STRONG BUY)
- Near-term growth is important (quick recoveries OR continued ascent)
- New highs are valid trades (momentum), not exit signals
- Penalties are light - we surface opportunities for user investigation
- Risk is acceptable - this is for swing trades not buy-and-hold

### Success Criteria
- **STRONG BUY** (75+): Top 10-20% of opportunities - clear setups worth immediate attention
- **BUY** (55-74): Good setups - worth investigating if you have bandwidth
- **HOLD** (45-54): Neutral - not compelling but not broken
- **AVOID** (0-44): Filter out the noise - save time by skipping these

### Use Case: Scanning Large Watchlists
When running scores across 50-100+ stocks:
- STRONG BUY should surface the top 5-15 opportunities (not 40+)
- BUY expands to maybe 20-30 stocks worth reviewing
- AVOID should eliminate at least 40-50% of the list (noise reduction)
- Clear differentiation prevents "everything looks the same"

## Investment Score (Long-term Quality Assessment)

### Purpose
Identify quality growth stocks worth holding long-term with acceptable volatility and strong company fundamentals.

**Philosophy**: Less risky than trades, favor strong companies. Willing to hold through volatility if growth trajectory is intact.

### Time Horizon
- Primary: Months to years
- Validation: 3-month forward returns

### Focus Areas
1. **Bottom confirmation** - Wait for clearer signs price has bottomed (not early entry like Trade)
2. **Lower volatility** - Acceptable volatility for long-term holding
3. **Growth trajectory** - Net upward path with growth potential in next few months
4. **Company strength** - Solid fundamentals, resilience, quality
5. **Risk management** - Less risky than swing trades

### Examples

**KEEP (High Score):**
- **RKLB**: Volatile BUT recovers quickly AND net growth path = acceptable
- **GOOGL/MSFT**: Solid companies with acceptable volatility = ideal

**AVOID (Low Score):**
- **IBIT**: Structural decline, high volatility, no growth trajectory
- **CRWV**: Severe decline, no resilience, poor fundamentals

### Key Indicators
- **Bottom confirmation signals** - Stabilization, RSI recovery, holding above recent low
- **Volatility** - Daily sigma (prefer < 3% "choppy", avoid "wild")
- **Growth rate** - 1-year annualized growth (prefer > 20%)
- **Trend slope** - Long-term trajectory steepness (100-day)
- **Resilience** - Quick recovery ability (bounce-back count)
- **Long-term trend** - 100-day trend bias (must be UP or recovering to UP)
- **Rally magnitude** - Historical upside potential (90-day max rally)
- **Return to highs frequency** - Time spent near highs (consistency)

### Scoring Logic

**Philosophy**: Conservative, quality-focused. Wait for bottom confirmation, favor low volatility and strong growth trajectory.

```
Start at 50 (neutral)

GROWTH & TRAJECTORY (primary signals):
+ 1-year growth rate > 50% = +25 (exceptional growth)
+ 1-year growth rate > 20% = +15 (strong growth)
+ 1-year growth rate > 0% = +5 (positive growth)
+ Trend slope (100d) > 30% annualized = +15 (steep trajectory)
+ Trend slope (100d) > 10% annualized = +10 (solid trajectory)
+ Long-term trend (100d) UP = +15 (structural uptrend)

QUALITY & RESILIENCE (company strength):
+ High resilience count (3+ recoveries) = +15 (bounce-back ability)
+ Return to highs frequency > 50% = +10 (consistent performer)
+ Rally magnitude > 100% = +10 (explosive upside potential)
+ Rally magnitude > 50% = +5

VOLATILITY (risk awareness - prefer lower but not disqualifying):
+ Calm volatility (< 1% sigma) = +10 (ideal for comfort)
+ Choppy volatility (1-3% sigma) = +3 (acceptable)
+ Wild volatility (> 3% sigma) = -5 (note the risk, but growth can compensate)

BOTTOM CONFIRMATION (conservative entry):
+ RSI > 40 (not in freefall) = +10
+ Price holding above 5-day low = +5 (stabilization)
+ Above SMA(100) = +10 (long-term support intact)

STRUCTURAL DECLINE (major penalties):
- Severe slope decline (< -30% annualized) = -40 (avoid IBIT/CRWV)
- Negative 1-year growth = -20 (declining, not growing)
- No resilience history (count = 0) = -10 (unproven recovery ability)
- Very extended drop (> -40% from high) = -20 (might be structural)
```

**Expected Results:**
- **GOOGL/MSFT**: Growth ~30%, low vol, resilient → Score ~85 (STRONG BUY)
- **RKLB**: Growth ~70%, high vol BUT resilient, rally >100% → Score ~70 (BUY)
- **IBIT**: Growth -79%, high vol, declining → Score ~25 (SELL)

**Design Notes**:
- Growth trajectory weighted heavily (up to +55)
- Volatility matters for long-term holding (-15 for wild)
- Bottom confirmation prevents early entry (wait for stabilization)
- Structural decline heavily penalized (-40 to -80 total)
- Quality companies with acceptable volatility score 60-85

### Success Criteria
- **STRONG BUY** (80+): Exceptional companies like GOOGL/MSFT - low volatility, strong growth
- **BUY** (60-79): Quality growth like RKLB - acceptable volatility, resilient, net growth
- **HOLD** (45-59): Decent but not compelling - might hold existing positions
- **UNDERPERFORM** (30-44): Weak quality - consider reducing/exiting
- **SELL** (0-29): Poor quality like IBIT/CRWV - structural decline, avoid

### Use Case: Scanning Large Watchlists
When running scores across 50-100+ stocks:
- STRONG BUY should identify 5-10 exceptional quality companies
- BUY should identify 15-25 quality growth stocks worth holding
- SELL/UNDERPERFORM should eliminate declining/risky stocks (~30-40%)

## Lessons from v1.0-1.4.x

### What We Learned
1. **Don't mix concerns**: Trade and Investment serve different purposes - keep them completely separate
2. **Time horizons matter**: Short-term (days/weeks) vs long-term (months/years) require different indicators
3. **Validate independently**: Backtest each score at its appropriate time horizon (1mo vs 3mo)
4. **Pattern bonuses can mislead**: Recovery patterns work differently on trending vs declining stocks
5. **Simple is better**: Start with clean, understandable logic before adding complexity

### What Worked
- Separate rating thresholds for Trade vs Investment
- Backtest infrastructure for validation
- ScoreResult dataclass for dual-score tracking
- Diagnostic tools for debugging specific dates

### What Didn't Work
- Mixing Trade and Investment logic (led to confusion)
- Pattern bonuses triggering incorrectly on declining stocks
- Score inversion hacks (symptom of deeper design issues)
- Too much complexity without clear purpose

## Implementation Approach

### Phase 1: Plan Trade Score
1. Define objective clearly
2. Choose relevant indicators
3. Design scoring logic
4. Document expected behavior

### Phase 2: Implement & Validate Trade Score
1. Implement calculate_trade_score()
2. Backtest on multiple tickers (NVDA, GOOGL, RKLB, IBIT)
3. Evaluate at 1-month time horizon
4. Iterate until success criteria met

### Phase 3: Plan Investment Score
1. Define objective clearly (independent of Trade Score)
2. Choose relevant indicators
3. Design scoring logic
4. Document expected behavior

### Phase 4: Implement & Validate Investment Score
1. Implement calculate_investment_score()
2. Backtest on multiple tickers
3. Evaluate at 3-month time horizon
4. Iterate until success criteria met

### Phase 5: Final Validation
1. Run both scores on full watchlist
2. Verify independence (changing one doesn't affect the other)
3. Validate against known cases (e.g., IBIT should rate poorly)
4. Document final methodology

## Critical Files

### `/Users/nigel/Projects/Iceberg/src/iceberg/analysis/scoring.py`
Contains both scoring functions - keep them independent!

### `/Users/nigel/Projects/Iceberg/src/iceberg/analysis/indicators.py`
Shared technical indicator calculations - both scores use these.

### `/Users/nigel/Projects/Iceberg/src/iceberg/analysis/backtest.py`
Validation tool - evaluates scores at appropriate time horizons.

### `/Users/nigel/Projects/Iceberg/src/iceberg/analysis/diagnose.py`
Debug tool - inspects scores on specific dates.

## Next Steps

1. **Define Trade Score logic** - What indicators and weights?
2. **Define Investment Score logic** - What indicators and weights?
3. **Implement Trade Score** - Build and validate
4. **Implement Investment Score** - Build and validate
5. **Final validation** - Test both scores independently

---

*This plan will be filled in collaboratively with detailed scoring logic for each score.*
