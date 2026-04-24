"""Build Plotly charts for stock price visualization."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import db
import data as data_module

# Distinct colors for stocks. MA uses same color but dashed.
STOCK_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
]


def _lighten_color(hex_color: str, factor: float = 0.4) -> str:
    """Make a hex color lighter by mixing with white."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def get_next_color(existing_colors: list[str]) -> str:
    """Pick the next unused color from the palette."""
    used = set(existing_colors)
    for color in STOCK_COLORS:
        if color not in used:
            return color
    # Fallback: cycle
    return STOCK_COLORS[len(existing_colors) % len(STOCK_COLORS)]


def _filter_by_date(df: pd.DataFrame, start_date: str | None, end_date: str | None) -> pd.DataFrame:
    """Filter a price DataFrame by date range."""
    if df.empty:
        return df
    filtered = df.copy()
    if start_date:
        filtered = filtered[filtered["date"] >= pd.Timestamp(start_date)]
    if end_date:
        filtered = filtered[filtered["date"] <= pd.Timestamp(end_date)]
    return filtered.reset_index(drop=True)


def _to_percentage_return(df: pd.DataFrame) -> pd.DataFrame:
    """Convert close and 200_week_ma columns to percentage return from first value."""
    if df.empty or len(df) < 1:
        return df
    result = df.copy()
    base_price = result["close"].iloc[0]
    if base_price == 0:
        return result
    result["close"] = ((result["close"] / base_price) - 1) * 100
    if "200_week_ma" in result.columns:
        # MA may have NaN at start; use first non-NaN MA as base, or price base
        ma_valid = result["200_week_ma"].dropna()
        if not ma_valid.empty:
            ma_base = base_price  # same base as price for consistent comparison
            result["200_week_ma"] = ((result["200_week_ma"] / ma_base) - 1) * 100
    return result


def build_combined_chart(stocks: list[dict], y_mode: str = "price",
                         start_date: str | None = None,
                         end_date: str | None = None) -> go.Figure:
    """Build a single chart with all stocks overlaid.

    Args:
        y_mode: "price" for absolute prices, "return" for percentage return.
        start_date: ISO date string for window start.
        end_date: ISO date string for window end.
    """
    fig = go.Figure()

    if not stocks:
        fig.update_layout(
            title="No stocks added yet",
            xaxis_title="Date",
            yaxis_title="Price",
            template="plotly_white",
        )
        return fig

    y_label = "Return (%)" if y_mode == "return" else "Price"
    value_label = "Return" if y_mode == "return" else "Price"
    value_fmt = "%{y:.1f}%" if y_mode == "return" else "%{y:.2f}"

    for stock in stocks:
        prices = db.get_prices(stock["id"])
        if prices.empty:
            continue
        prices = data_module.compute_200_week_ma(prices)
        prices = _filter_by_date(prices, start_date, end_date)
        if prices.empty:
            continue
        if y_mode == "return":
            prices = _to_percentage_return(prices)
        color = stock["color"]

        fig.add_trace(go.Scatter(
            x=prices["date"],
            y=prices["close"],
            name=stock["display_name"],
            line={"color": color, "width": 2},
            hovertemplate="%{x|%Y-%m-%d}<br>" + value_label + ": " + value_fmt + "<extra>" + stock["display_name"] + "</extra>",
        ))

        if stock["show_ma"]:
            fig.add_trace(go.Scatter(
                x=prices["date"],
                y=prices["200_week_ma"],
                name=f"{stock['display_name']} 200w MA",
                line={"color": _lighten_color(color), "width": 1.5, "dash": "dash"},
                hovertemplate="%{x|%Y-%m-%d}<br>200w MA: " + value_fmt + "<extra>" + stock["display_name"] + "</extra>",
            ))

    fig.update_layout(
        title="Stock Prices & 200-Week Moving Average",
        xaxis_title="Date",
        yaxis_title=y_label,
        template="plotly_white",
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
        margin={"l": 50, "r": 20, "t": 60, "b": 50},
    )
    return fig


def build_individual_charts(stocks: list[dict], y_mode: str = "price",
                            start_date: str | None = None,
                            end_date: str | None = None) -> list[go.Figure]:
    """Build one chart per stock."""
    figures = []
    y_label = "Return (%)" if y_mode == "return" else "Price"
    value_label = "Return" if y_mode == "return" else "Price"
    value_fmt = "%{y:.1f}%" if y_mode == "return" else "%{y:.2f}"

    for stock in stocks:
        prices = db.get_prices(stock["id"])
        if prices.empty:
            continue
        prices = data_module.compute_200_week_ma(prices)
        prices = _filter_by_date(prices, start_date, end_date)
        if prices.empty:
            continue
        if y_mode == "return":
            prices = _to_percentage_return(prices)
        color = stock["color"]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=prices["date"],
            y=prices["close"],
            name=value_label,
            line={"color": color, "width": 2},
            hovertemplate="%{x|%Y-%m-%d}<br>" + value_label + ": " + value_fmt + "<extra></extra>",
        ))

        if stock["show_ma"]:
            fig.add_trace(go.Scatter(
                x=prices["date"],
                y=prices["200_week_ma"],
                name="200w MA",
                line={"color": _lighten_color(color), "width": 1.5, "dash": "dash"},
                hovertemplate="%{x|%Y-%m-%d}<br>200w MA: " + value_fmt + "<extra></extra>",
            ))

        fig.update_layout(
            title=f"{stock['display_name']} ({stock['ticker']})",
            xaxis_title="Date",
            yaxis_title=y_label,
            template="plotly_white",
            hovermode="x unified",
            margin={"l": 50, "r": 20, "t": 50, "b": 50},
        )
        figures.append(fig)

    return figures
