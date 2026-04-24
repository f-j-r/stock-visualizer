# Stock Visualizer

> *"If all you ever did was buy high-quality stocks on the 200-week moving average, you would beat the S&P 500 by a large margin over time."*
> — widely attributed to Charlie Munger (exact origin debated)

A web-based stock price visualizer with 200-week moving average tracking, Telegram price alerts, and percentage return analysis.

## Features

- **Add stocks** by ISIN, WKN, ticker symbol, or index (e.g. `^GSPC`)
- **200-week moving average** overlay per stock (toggleable, only shown after 200 weeks of data)
- **Combined or individual** chart views
- **Percentage return** or absolute price Y-axis (switchable)
- **Date range filter** to analyze specific time windows
- **Telegram alerts** when a stock crosses below a configurable threshold relative to the 200-week MA
- **Persistent storage** — stocks and cached price data survive restarts (SQLite)
- **Incremental data updates** — only fetches new data from Yahoo Finance
- **Mobile-friendly** — works in any browser

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
# Open http://localhost:8050
```

## Docker

```bash
cp .env.example .env   # edit with your settings
docker compose up --build
```

## Configuration

All settings via environment variables (or `.env` file):

| Variable | Default | Description |
|---|---|---|
| `SV_DB_PATH` | `data/stocks.db` | SQLite database path |
| `SV_TELEGRAM_BOT_TOKEN` | _(empty)_ | Telegram bot token for alerts |
| `SV_TELEGRAM_CHAT_ID` | _(empty)_ | Telegram chat ID for alerts |
| `SV_ALERT_CHECK_HOURS` | `4` | Alert check interval in hours |
| `SV_ALERT_THRESHOLD_PERCENT` | `0` | Alert threshold relative to 200w MA (0 = at MA, +10 = 10% above, -10 = 10% below) |
| `SV_HOST` | `0.0.0.0` | Server bind address |
| `SV_PORT` | `8050` | Server port |
| `SV_DEBUG` | `false` | Enable debug mode |

## Tests

```bash
python -m pytest tests/ -v
```

## Data Source

Price data is fetched from [Yahoo Finance](https://finance.yahoo.com/) via `yfinance`. MSCI indices are not directly available — use tracking ETFs instead (e.g. `URTH` or `IWDA.AS` for MSCI World).
