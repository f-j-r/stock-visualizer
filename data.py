"""Fetch stock data from Yahoo Finance. Resolve ISIN/WKN to ticker symbols."""

import logging
from datetime import datetime, timedelta

import pandas as pd
import requests
import yfinance as yf

import db

logger = logging.getLogger(__name__)

YAHOO_SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"


def resolve_to_ticker(identifier: str) -> dict | None:
    """Resolve an ISIN, WKN, or ticker to a Yahoo Finance ticker symbol.

    Returns dict with keys: ticker, name, identifier_type, or None if not found.
    """
    identifier = identifier.strip().upper()
    identifier_type = _guess_identifier_type(identifier)

    # If it looks like a ticker, verify it exists
    if identifier_type == "ticker":
        info = _verify_ticker(identifier)
        if info:
            return {"ticker": identifier, "name": info, "identifier_type": "ticker"}

    # Search Yahoo Finance for ISIN/WKN/unknown
    result = _search_yahoo(identifier)
    if result:
        result["identifier_type"] = identifier_type
        return result

    return None


def _guess_identifier_type(identifier: str) -> str:
    """Heuristic to determine identifier type."""
    if len(identifier) == 12 and identifier[:2].isalpha():
        return "isin"
    if len(identifier) == 6 and identifier.isalnum():
        return "wkn"
    if identifier.startswith("^"):
        return "index"
    return "ticker"


def _verify_ticker(ticker: str) -> str | None:
    """Check if a ticker is valid. Returns the short name or None."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        return info.get("shortName") or info.get("longName") or ticker
    except Exception:
        return None


def _search_yahoo(query: str) -> dict | None:
    """Search Yahoo Finance for a symbol matching the query."""
    try:
        resp = requests.get(
            YAHOO_SEARCH_URL,
            params={"q": query, "quotesCount": 5, "newsCount": 0},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        quotes = data.get("quotes", [])
        if not quotes:
            return None
        # Prefer exact match, fallback to first result
        best = quotes[0]
        return {
            "ticker": best["symbol"],
            "name": best.get("shortname") or best.get("longname") or best["symbol"],
        }
    except Exception as e:
        logger.warning("Yahoo search failed for '%s': %s", query, e)
        return None


def fetch_weekly_prices(ticker: str, start_date: str | None = None) -> pd.DataFrame:
    """Download weekly closing prices from Yahoo Finance.

    Args:
        ticker: Yahoo Finance ticker symbol.
        start_date: ISO date string to fetch from (for incremental updates).
                    If None, fetches max available history.

    Returns:
        DataFrame with columns: date, close.
    """
    try:
        t = yf.Ticker(ticker)
        if start_date:
            # Fetch from a bit before start_date to ensure overlap
            start = (pd.Timestamp(start_date) - timedelta(days=7)).strftime("%Y-%m-%d")
            df = t.history(start=start, interval="1wk")
        else:
            df = t.history(period="max", interval="1wk")

        if df.empty:
            return pd.DataFrame(columns=["date", "close"])

        df = df.reset_index()
        df = df.rename(columns={"Date": "date", "Close": "close"})
        df = df[["date", "close"]].dropna()
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        return df

    except Exception as e:
        logger.error("Failed to fetch prices for %s: %s", ticker, e)
        return pd.DataFrame(columns=["date", "close"])


def update_stock_prices(stock_id: int, ticker: str):
    """Fetch new prices and save to database (incremental)."""
    last_date = db.get_last_price_date(stock_id)
    df = fetch_weekly_prices(ticker, start_date=last_date)
    if not df.empty:
        db.save_prices(stock_id, df)


def update_all_stocks():
    """Refresh price data for all tracked stocks."""
    stocks = db.get_stocks()
    for stock in stocks:
        logger.info("Updating prices for %s (%s)", stock["display_name"], stock["ticker"])
        update_stock_prices(stock["id"], stock["ticker"])


def compute_200_week_ma(df: pd.DataFrame) -> pd.DataFrame:
    """Add a '200_week_ma' column to a price DataFrame."""
    if df.empty:
        df["200_week_ma"] = pd.Series(dtype=float)
        return df
    result = df.copy()
    result["200_week_ma"] = result["close"].rolling(window=200, min_periods=200).mean()
    return result
