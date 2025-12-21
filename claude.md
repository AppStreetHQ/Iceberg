# Iceberg Terminal

## The Name

Like a Bloomberg terminal, but called **Iceberg** - because 2/3 of the portfolio is underwater. 🧊📉

## The Vibe

We’re building a slick, information-dense terminal UI in Python that feels like a Bloomberg terminal - lots of live data, multiple panes, professional aesthetic. Pure vibe-coding, we’ll iterate and add cool stuff as we go.

## Tech Stack

- **Textual** - Modern Python TUI framework
- **Rich** - For beautiful terminal rendering
- **SQLite** - Local database for price history
- APIs for market data (see below)

## Core Features

- Multi-pane layout with live updating data
- **Watchlist panel** with price tickers (left side)
 - Shows ticker symbol, current price, and price change ($ and %)
 - Color-coded: green for gains, red for losses
 - Change calculated from closing price (or latest if market open)
 - Arrow keys or j/k to cycle through tickers
 - Highlighted selection shows which ticker is active
- **Chart panel** displays selected ticker’s price history
 - ASCII-style charts using **asciichartpy** (Unicode box-drawing chars)
 - **Absolute price chart** - actual price values over selected range
 - **Relative price chart** - percentage change from first price in the window (normalized to starting point)
 - Responds to global day range setting
 - **Calculated on demand** - show loading indicator while computing
 - Retro terminal aesthetic but modern Unicode rendering
 - (Previous Swift attempt: CLI charts worked great, TUI framework failed - we want to replicate the chart logic in Python/Textual)
- **Technical analysis panel** shows metrics for selected ticker
 - Key indicators: RSI, MACD, moving averages, volume trends
 - Visual status indicators using emoji: 🐂🐻 for sentiment, 🔴🟠🟢 for signal strength
 - Modern touch on retro aesthetic - emoji pops against monospace terminal vibe
 - Quick at-a-glance signal strength
 - Updates when ticker selection changes
 - **Calculated on demand** - show loading indicator while computing
 - **Custom analysis section** - space to experiment with homegrown indicators
   - Keep it simple, make it fun
   - Ideas: pattern recognition, momentum signals, volatility measures, custom ratios
   - Room to vibe-code new ideas and see what sticks
   - Easy to add/remove experimental features
   - Modular design - drop in new analysis functions without breaking existing stuff
- Sparkline/mini charts for price movement
- News/info ticker scrolling across bottom
- Clean, readable dark theme with color-coded gains/losses

## Interaction Model

- **Selected ticker** in watchlist drives what displays in other panes
- Up/Down arrows (or j/k vim-style) to navigate watchlist
- **Tab** to switch focus between panes
- When chart pane is focused: toggle between absolute/relative view
- Day range controls (7d, 30d, 90d, 1yr, etc.)
 - Some TA will be fixed (like 20-day moving average)
 - Some can be based on selected range
 - Range should be outside chart pane and applied to all panes as required
- All charts and analysis update based on current selection
- Hotkey to fetch fresh prices from API → updates DB

## Layout Sketch

```
┌─────────────────────────────────────────────────────┐
│ MARKET INDICES (SPY, QQQ, DIA as proxies)           │
├──────────────┬──────────────────────────────────────┤
│              │                                      │
│  WATCHLIST   │         MAIN DISPLAY                │
│              │    (charts + technical analysis)     │
│              │                                      │
│              │                                      │
├──────────────┴──────────────────────────────────────┤
│ NEWS TICKER / STATUS BAR                            │
└─────────────────────────────────────────────────────┘
```

## Panes

- **Market Indices** - Top banner showing major indices using ETF proxies
 - SPY (S&P 500), QQQ (NASDAQ), DIA (Dow), IWM (Russell 2000)
 - Quick snapshot: current price, day change with ↑↓ arrows and colors
 - Always visible, not part of watchlist
- **Watchlist** - Your specific tickers (left side)
 - Shows ticker symbol, current price, and price change ($ and %)
 - Color-coded: green for gains, red for losses
 - Change calculated from closing price (or latest if market open)
 - Arrow keys or j/k to cycle through tickers
 - Highlighted selection shows which ticker is active
- **Main Display** - Charts and technical analysis for selected ticker
- **Status Bar** - News ticker, last update time, hotkey hints

## Data Strategy

- **SQLite database** for all price storage
 - Daily OHLC data: Open, High, Low, Close (whatever Finnhub free tier provides)
 - Volume and other metadata from API response
 - No intraday prices - just daily snapshots
 - Latest prices when market is open (updated via hotkey)
 - Existing SQLite database can be found in ../StockStreet/Data/stockstreet.sqlite - try and share this if possible
- **Hotkey-triggered updates** - user presses a key to fetch and store latest prices
- APIs only called on-demand (no constant polling)
- Fast reads from local DB for display updates

## Data Sources (for manual updates)

- **Finnhub.io API** (free tier) for stock data
 - API key will be provided/configured
 - Store in environment variable or config file
 - **US exchanges only** (NYSE, NASDAQ, etc.)
- CoinGecko API for crypto prices (if we add crypto)
- RSS feeds for news tickers

## Development Approach

- Start with basic layout and static data
- Add one data source at a time
- Iterate on visual polish
- Keep it modular - easy to add/remove features
- Focus on making it feel smooth and responsive
- Have fun with it!

## Nice-to-haves (if we get there)

- Configurable watchlists
- Save/load layout preferences
- Multiple “workspaces”
- Alerts/notifications
- Export data to CSV
- Custom color schemes/themes
