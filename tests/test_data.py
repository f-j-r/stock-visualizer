"""Tests for data processing functions."""

import pandas as pd

from data import compute_200_week_ma, _guess_identifier_type


def test_guess_identifier_type_isin():
    assert _guess_identifier_type("US0378331005") == "isin"


def test_guess_identifier_type_wkn():
    assert _guess_identifier_type("865985") == "wkn"


def test_guess_identifier_type_ticker():
    assert _guess_identifier_type("AAPL") == "ticker"
    assert _guess_identifier_type("MSFT") == "ticker"


def test_guess_identifier_type_index():
    assert _guess_identifier_type("^GSPC") == "index"
    assert _guess_identifier_type("^GDAXI") == "index"


def test_compute_200_week_ma():
    dates = pd.date_range("2020-01-01", periods=250, freq="W")
    prices = pd.DataFrame({"date": dates, "close": range(1, 251)})

    result = compute_200_week_ma(prices)
    assert "200_week_ma" in result.columns
    assert len(result) == 250

    # First 199 rows should be NaN (not enough data)
    assert result.iloc[198]["200_week_ma"] != result.iloc[198]["200_week_ma"]  # NaN
    # Row 199 (200th data point) is the first valid MA
    # For linearly increasing data 1..200, mean = 100.5
    assert abs(result.iloc[199]["200_week_ma"] - 100.5) < 0.01


def test_compute_200_week_ma_empty():
    df = pd.DataFrame(columns=["date", "close"])
    result = compute_200_week_ma(df)
    assert "200_week_ma" in result.columns
    assert result.empty
