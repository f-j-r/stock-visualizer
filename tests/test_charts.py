"""Tests for chart building functions."""

import os
import tempfile

import pandas as pd

os.environ.setdefault("SV_DB_PATH", os.path.join(tempfile.mkdtemp(), "test_charts.db"))

import db
from charts import get_next_color, _lighten_color, build_combined_chart


def test_get_next_color():
    color1 = get_next_color([])
    assert color1.startswith("#")
    color2 = get_next_color([color1])
    assert color2 != color1


def test_lighten_color():
    lighter = _lighten_color("#000000", 0.5)
    # Black lightened 50% should be grey-ish
    assert lighter == "#7f7f7f"


def test_build_combined_chart_empty():
    db.init_db()
    fig = build_combined_chart([])
    assert fig.layout.title.text == "No stocks added yet"


def test_build_combined_chart_with_stock():
    db.init_db()
    stock_id = db.add_stock("TEST", "ticker", "TEST", "Test Stock", "#1f77b4")
    prices = pd.DataFrame({
        "date": pd.date_range("2020-01-01", periods=10, freq="W"),
        "close": [100 + i for i in range(10)],
    })
    db.save_prices(stock_id, prices)

    stock = db.get_stocks()[0]
    fig = build_combined_chart([stock])
    # Should have 2 traces: price + MA
    assert len(fig.data) == 2
