"""Tests for the database module."""

import os
import tempfile

import pandas as pd
import pytest

# Override DB path before importing db
os.environ["SV_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

import db


@pytest.fixture(autouse=True)
def fresh_db():
    """Ensure a clean database for each test."""
    db.init_db()
    # Clear all data before each test
    with db.get_db() as conn:
        conn.execute("DELETE FROM alerts")
        conn.execute("DELETE FROM prices")
        conn.execute("DELETE FROM stocks")
    yield


def test_add_and_get_stocks():
    stock_id = db.add_stock("AAPL", "ticker", "AAPL", "Apple Inc.", "#1f77b4")
    stocks = db.get_stocks()
    assert len(stocks) == 1
    assert stocks[0]["ticker"] == "AAPL"
    assert stocks[0]["display_name"] == "Apple Inc."
    assert stocks[0]["id"] == stock_id


def test_remove_stock():
    stock_id = db.add_stock("MSFT", "ticker", "MSFT", "Microsoft", "#ff7f0e")
    db.remove_stock(stock_id)
    assert len(db.get_stocks()) == 0


def test_save_and_get_prices():
    stock_id = db.add_stock("TSLA", "ticker", "TSLA", "Tesla", "#2ca02c")
    prices = pd.DataFrame({
        "date": pd.date_range("2023-01-01", periods=5, freq="W"),
        "close": [100.0, 102.0, 98.0, 105.0, 110.0],
    })
    db.save_prices(stock_id, prices)

    loaded = db.get_prices(stock_id)
    assert len(loaded) == 5
    assert loaded["close"].iloc[0] == 100.0


def test_last_price_date():
    stock_id = db.add_stock("GOOG", "ticker", "GOOG", "Google", "#d62728")
    assert db.get_last_price_date(stock_id) is None

    prices = pd.DataFrame({
        "date": ["2024-01-07", "2024-01-14"],
        "close": [150.0, 155.0],
    })
    db.save_prices(stock_id, prices)
    assert db.get_last_price_date(stock_id) == "2024-01-14"


def test_toggle_ma():
    stock_id = db.add_stock("AMZN", "ticker", "AMZN", "Amazon", "#9467bd")
    db.toggle_ma(stock_id, False)
    stocks = db.get_stocks()
    assert stocks[0]["show_ma"] == 0

    db.toggle_ma(stock_id, True)
    stocks = db.get_stocks()
    assert stocks[0]["show_ma"] == 1


def test_alert_state():
    stock_id = db.add_stock("NVDA", "ticker", "NVDA", "NVIDIA", "#8c564b")
    state = db.get_alert_state(stock_id)
    assert state is not None
    assert state["was_below_ma"] == 0

    db.update_alert_state(stock_id, True, "2024-01-15")
    state = db.get_alert_state(stock_id)
    assert state["was_below_ma"] == 1
    assert state["last_alert_date"] == "2024-01-15"
