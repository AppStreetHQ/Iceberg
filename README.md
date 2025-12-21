# Iceberg Terminal 🧊

Like a Bloomberg terminal, but called **Iceberg** - because 2/3 of the portfolio is underwater.

A beautiful, information-dense Python TUI for stock market analysis with technical indicators, built with [Textual](https://textual.textualize.io/).

## Features

- **Multi-pane layout** with live updating data
- **Market Indices** banner showing SPY, QQQ, DIA, IWM
- **Watchlist panel** with price tickers and color-coded gains/losses
- **Chart panel** with ASCII-style charts (absolute price and relative % change modes)
- **Technical analysis panel** with MACD, RSI, SMA, Trend, and Volatility indicators
- **Keyboard-driven navigation** (j/k or arrows, Tab to switch panes)
- **Emoji indicators** for at-a-glance signal strength (🐂🐻🟢🟠🔴)

## Installation

### Requirements

- Python 3.9+
- Access to the StockStreet database at `../StockStreet/Data/stockstreet.sqlite`

### Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .

# Run the terminal
python -m iceberg
```

## Usage

### Keyboard Controls

- **j / k** or **↑ / ↓**: Navigate watchlist
- **c**: Toggle chart mode (absolute price ↔ relative % change)
- **r**: Cycle day range (7d → 30d → 90d → 1yr)
- **q**: Quit

### Layout

```
┌─────────────────────────────────────────────────────┐
│ MARKET INDICES (SPY, QQQ, DIA, IWM)                 │
├──────────────┬──────────────────────────────────────┤
│              │                                      │
│  WATCHLIST   │         CHARTS                      │
│              │                                      │
│              ├──────────────────────────────────────┤
│              │                                      │
│              │    TECHNICAL ANALYSIS                │
│              │                                      │
├──────────────┴──────────────────────────────────────┤
│ STATUS BAR (hints and info)                         │
└─────────────────────────────────────────────────────┘
```

## Technical Indicators

All indicators ported from the Swift StockStreet project:

- **MACD(12,26,9)**: Exponential moving averages with histogram, signal line
- **RSI(14)**: Relative strength with 5-tier classification (oversold to overbought)
- **SMA(20)**: Simple moving average with trend classification
- **Trend**: Compares current price to SMA (up >2%, down <-2%, sideways)
- **Volatility (σ)**: Standard deviation of daily returns (calm <1%, choppy 1-3%, wild >3%)
- **Direction**: Today's momentum vs yesterday

## Data Source

Iceberg shares the SQLite database with the StockStreet Swift project:

- **Database**: `../StockStreet/Data/stockstreet.sqlite`
- **Watchlist**: `../StockStreet/Data/nasdaq100.csv`

The database contains daily OHLCV data fetched from Finnhub API.

## Project Structure

```
src/iceberg/
├── __init__.py
├── __main__.py          # Entry point
├── app.py               # Main Textual app
├── app.tcss             # CSS styling
├── config.py            # Configuration
├── data/                # Data layer
│   ├── db.py            # SQLite queries
│   ├── models.py        # DailyPrice, WatchlistItem
│   └── loader.py        # CSV loading
├── analysis/            # Technical analysis
│   ├── indicators.py    # MACD, RSI, SMA, etc.
│   └── models.py        # Result models
├── widgets/             # Textual widgets
│   ├── market_indices.py
│   ├── watchlist.py
│   ├── chart.py
│   ├── technical_panel.py
│   └── status_bar.py
└── utils/
    └── formatting.py    # Price/color helpers
```

## Development

### Testing

```bash
# Test imports
python -c "from iceberg.app import IcebergApp; print('✓ OK')"

# Test database connection
python -c "from iceberg.config import Config; from iceberg.data.db import Database; db = Database(Config.load().db_path); print(db.get_latest_price('AAPL'))"

# Test indicators
python -c "from iceberg.data.db import Database; from iceberg.config import Config; from iceberg.analysis.indicators import compute_rsi; closes = Database(Config.load().db_path).get_closing_prices('AAPL', 90); print(compute_rsi(closes))"
```

### Dependencies

- **textual**: Modern TUI framework
- **rich**: Terminal rendering
- **asciichartpy**: ASCII chart generation

## Future Enhancements

- [ ] Hotkey to fetch fresh prices from Finnhub API
- [ ] Scrolling news ticker
- [ ] Custom analysis section for experimental indicators
- [ ] Configurable watchlists
- [ ] Multiple workspaces
- [ ] Export data to CSV

## License

This is a hobby project. Have fun with it!

---

**Note**: This is the Python reboot of the Swift StockStreet project, which hit a dead end with TUI frameworks in Swift. Textual makes building terminal UIs in Python a joy! 🎉
