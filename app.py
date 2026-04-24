"""Stock Visualizer — Dash web application."""

import logging

from dash import Dash, html, dcc, Input, Output, State, callback, ALL, ctx, no_update
import dash

import db
import data as data_module
import charts
import alerts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

db.init_db()

app = Dash(__name__, title="Stock Visualizer", suppress_callback_exceptions=True)

app.layout = html.Div([
    # Header
    html.H1("Stock Visualizer", style={"textAlign": "center", "marginBottom": "10px"}),
    html.P(
        "Track stocks with their 200-week moving average",
        style={"textAlign": "center", "color": "#666", "marginTop": "0"},
    ),

    # Controls bar
    html.Div([
        # Add stock input
        html.Div([
            dcc.Input(
                id="stock-input",
                type="text",
                placeholder="ISIN, WKN, ticker, or index (e.g. ^GSPC)...",
                debounce=True,
                style={"width": "250px", "padding": "8px", "fontSize": "14px"},
            ),
            html.Button(
                "Add Stock",
                id="add-button",
                n_clicks=0,
                style={
                    "padding": "8px 16px", "marginLeft": "8px",
                    "fontSize": "14px", "cursor": "pointer",
                },
            ),
        ], style={"display": "flex", "alignItems": "center"}),

        # View toggle
        html.Div([
            html.Label("View: ", style={"marginRight": "8px", "fontWeight": "bold"}),
            dcc.RadioItems(
                id="view-toggle",
                options=[
                    {"label": "Combined", "value": "combined"},
                    {"label": "Individual", "value": "individual"},
                ],
                value="combined",
                inline=True,
                style={"display": "flex", "gap": "12px"},
            ),
        ], style={"display": "flex", "alignItems": "center"}),

        # Refresh button
        html.Button(
            "↻ Refresh Data",
            id="refresh-button",
            n_clicks=0,
            style={"padding": "8px 16px", "fontSize": "14px", "cursor": "pointer"},
        ),
    ], style={
        "display": "flex", "justifyContent": "space-between", "alignItems": "center",
        "padding": "10px 20px", "backgroundColor": "#f8f9fa", "borderRadius": "8px",
        "marginBottom": "15px", "flexWrap": "wrap", "gap": "10px",
    }),

    # Second controls row: Y-axis mode + date range
    html.Div([
        # Y-axis toggle
        html.Div([
            html.Label("Y-Axis: ", style={"marginRight": "8px", "fontWeight": "bold"}),
            dcc.RadioItems(
                id="y-axis-toggle",
                options=[
                    {"label": "Price", "value": "price"},
                    {"label": "Return %", "value": "return"},
                ],
                value="return",
                inline=True,
                style={"display": "flex", "gap": "12px"},
            ),
        ], style={"display": "flex", "alignItems": "center"}),

        # Date range picker
        html.Div([
            html.Label("From: ", style={"marginRight": "4px", "fontWeight": "bold"}),
            dcc.DatePickerSingle(
                id="date-start",
                placeholder="Start date",
                display_format="YYYY-MM-DD",
                style={"marginRight": "12px"},
            ),
            html.Label("To: ", style={"marginRight": "4px", "fontWeight": "bold"}),
            dcc.DatePickerSingle(
                id="date-end",
                placeholder="End date",
                display_format="YYYY-MM-DD",
                style={"marginRight": "12px"},
            ),
            html.Button(
                "Reset Range",
                id="reset-range-button",
                n_clicks=0,
                style={"padding": "6px 12px", "fontSize": "13px", "cursor": "pointer"},
            ),
        ], style={"display": "flex", "alignItems": "center"}),
    ], style={
        "display": "flex", "justifyContent": "space-between", "alignItems": "center",
        "padding": "10px 20px", "backgroundColor": "#f0f1f3", "borderRadius": "8px",
        "marginBottom": "15px", "flexWrap": "wrap", "gap": "10px",
    }),

    # Status message
    html.Div(id="status-message", style={"padding": "0 20px", "color": "#666"}),

    # Stock list with remove/toggle controls
    html.Div(id="stock-list", style={"padding": "0 20px", "marginBottom": "10px"}),

    # Charts container
    html.Div(id="charts-container", style={"padding": "0 10px"}),

    # Hidden store for triggering updates
    dcc.Store(id="stocks-updated", data=0),

], style={
    "maxWidth": "1400px", "margin": "0 auto", "padding": "20px",
    "fontFamily": "Arial, sans-serif",
})


@callback(
    Output("stocks-updated", "data"),
    Output("status-message", "children"),
    Output("stock-input", "value"),
    Input("add-button", "n_clicks"),
    State("stock-input", "value"),
    State("stocks-updated", "data"),
    prevent_initial_call=True,
)
def add_stock(n_clicks, identifier, counter):
    """Resolve identifier and add stock to tracking."""
    if not identifier or not identifier.strip():
        return no_update, "Please enter a stock identifier.", no_update

    identifier = identifier.strip()

    # Check for duplicates
    existing = db.get_stocks()
    for s in existing:
        if s["identifier"].upper() == identifier.upper() or s["ticker"].upper() == identifier.upper():
            return no_update, f"'{identifier}' is already tracked.", ""

    # Resolve to ticker
    result = data_module.resolve_to_ticker(identifier)
    if not result:
        return no_update, f"Could not find '{identifier}'. Try a different identifier.", ""

    # Pick color
    existing_colors = [s["color"] for s in existing]
    color = charts.get_next_color(existing_colors)

    # Add to DB
    stock_id = db.add_stock(
        identifier=identifier,
        identifier_type=result["identifier_type"],
        ticker=result["ticker"],
        display_name=result["name"],
        color=color,
    )

    # Fetch initial price data
    data_module.update_stock_prices(stock_id, result["ticker"])

    return counter + 1, f"Added {result['name']} ({result['ticker']})", ""


@callback(
    Output("stocks-updated", "data", allow_duplicate=True),
    Output("status-message", "children", allow_duplicate=True),
    Input({"type": "remove-button", "index": ALL}, "n_clicks"),
    State("stocks-updated", "data"),
    prevent_initial_call=True,
)
def remove_stock(n_clicks_list, counter):
    """Remove a stock from tracking."""
    if not ctx.triggered_id or not any(n_clicks_list):
        return no_update, no_update

    stock_id = ctx.triggered_id["index"]
    stocks = db.get_stocks()
    name = next((s["display_name"] for s in stocks if s["id"] == stock_id), "Stock")
    db.remove_stock(stock_id)
    return counter + 1, f"Removed {name}"


@callback(
    Output("stocks-updated", "data", allow_duplicate=True),
    Input({"type": "ma-toggle", "index": ALL}, "value"),
    State("stocks-updated", "data"),
    prevent_initial_call=True,
)
def toggle_ma_visibility(toggle_values, counter):
    """Toggle 200-week MA display for a stock."""
    if not ctx.triggered_id:
        return no_update

    stock_id = ctx.triggered_id["index"]
    # Find the value for this specific toggle
    stocks = db.get_stocks()
    stock_ids = [s["id"] for s in stocks]
    if stock_id in stock_ids:
        idx = stock_ids.index(stock_id)
        show = bool(toggle_values[idx]) if idx < len(toggle_values) else True
        db.toggle_ma(stock_id, show)
    return counter + 1


@callback(
    Output("stocks-updated", "data", allow_duplicate=True),
    Output("status-message", "children", allow_duplicate=True),
    Input("refresh-button", "n_clicks"),
    State("stocks-updated", "data"),
    prevent_initial_call=True,
)
def refresh_data(n_clicks, counter):
    """Refresh price data for all stocks."""
    data_module.update_all_stocks()
    return counter + 1, "Data refreshed."


@callback(
    Output("stock-list", "children"),
    Input("stocks-updated", "data"),
)
def render_stock_list(counter):
    """Render the list of tracked stocks with controls."""
    stocks = db.get_stocks()
    if not stocks:
        return html.P("No stocks tracked. Add one above.", style={"color": "#999"})

    items = []
    for stock in stocks:
        items.append(html.Div([
            # Color indicator
            html.Span("●", style={"color": stock["color"], "fontSize": "20px", "marginRight": "8px"}),
            # Name
            html.Span(
                f"{stock['display_name']} ({stock['ticker']})",
                style={"marginRight": "12px", "fontWeight": "bold"},
            ),
            # MA toggle
            dcc.Checklist(
                id={"type": "ma-toggle", "index": stock["id"]},
                options=[{"label": "200w MA", "value": "show"}],
                value=["show"] if stock["show_ma"] else [],
                inline=True,
                style={"display": "inline-block", "marginRight": "12px"},
            ),
            # Remove button
            html.Button(
                "✕",
                id={"type": "remove-button", "index": stock["id"]},
                n_clicks=0,
                style={
                    "background": "none", "border": "1px solid #ddd", "borderRadius": "4px",
                    "cursor": "pointer", "color": "#999", "padding": "2px 8px",
                },
            ),
        ], style={
            "display": "flex", "alignItems": "center", "padding": "6px 0",
            "borderBottom": "1px solid #eee",
        }))

    return html.Div(items)


@callback(
    Output("date-start", "date"),
    Output("date-end", "date"),
    Input("reset-range-button", "n_clicks"),
    prevent_initial_call=True,
)
def reset_date_range(n_clicks):
    """Clear the date range filter."""
    return None, None


@callback(
    Output("charts-container", "children"),
    Input("stocks-updated", "data"),
    Input("view-toggle", "value"),
    Input("y-axis-toggle", "value"),
    Input("date-start", "date"),
    Input("date-end", "date"),
)
def render_charts(counter, view_mode, y_mode, start_date, end_date):
    """Render chart(s) based on the selected view mode and axis settings."""
    stocks = db.get_stocks()

    if not stocks:
        return html.Div()

    if view_mode == "combined":
        fig = charts.build_combined_chart(stocks, y_mode=y_mode,
                                          start_date=start_date, end_date=end_date)
        return dcc.Graph(
            figure=fig,
            style={"height": "600px"},
            config={"displayModeBar": True, "scrollZoom": True},
        )
    else:
        children = []
        figures = charts.build_individual_charts(stocks, y_mode=y_mode,
                                                 start_date=start_date, end_date=end_date)
        for fig in figures:
            children.append(dcc.Graph(
                figure=fig,
                style={"height": "450px", "marginBottom": "20px"},
                config={"displayModeBar": True, "scrollZoom": True},
            ))
        return html.Div(children)


if __name__ == "__main__":
    import config as cfg

    alerts.setup_scheduler(app)
    app.run(host=cfg.HOST, port=cfg.PORT, debug=cfg.DEBUG)
