"""SQLite database for persisting stocks, price data, and alert state."""

import os
import sqlite3
from contextlib import contextmanager

import pandas as pd

import config


def _ensure_dir():
    db_dir = os.path.dirname(config.DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)


def _get_connection() -> sqlite3.Connection:
    _ensure_dir()
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identifier TEXT NOT NULL,
                identifier_type TEXT NOT NULL,
                ticker TEXT NOT NULL,
                display_name TEXT NOT NULL,
                color TEXT NOT NULL,
                show_ma INTEGER NOT NULL DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS prices (
                stock_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                close REAL NOT NULL,
                FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
                PRIMARY KEY (stock_id, date)
            );

            CREATE TABLE IF NOT EXISTS alerts (
                stock_id INTEGER NOT NULL UNIQUE,
                last_alert_date TEXT,
                was_below_ma INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE
            );
        """)


def add_stock(identifier: str, identifier_type: str, ticker: str,
              display_name: str, color: str) -> int:
    """Insert a new stock. Returns the stock ID."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO stocks (identifier, identifier_type, ticker, display_name, color) "
            "VALUES (?, ?, ?, ?, ?)",
            (identifier, identifier_type, ticker, display_name, color),
        )
        stock_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO alerts (stock_id, was_below_ma) VALUES (?, 0)",
            (stock_id,),
        )
        return stock_id


def remove_stock(stock_id: int):
    """Delete a stock and its associated data."""
    with get_db() as conn:
        conn.execute("DELETE FROM stocks WHERE id = ?", (stock_id,))


def get_stocks() -> list[dict]:
    """Return all tracked stocks."""
    with get_db() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, identifier, identifier_type, ticker, display_name, color, show_ma "
            "FROM stocks ORDER BY added_at"
        ).fetchall()
        return [dict(r) for r in rows]


def toggle_ma(stock_id: int, show: bool):
    """Toggle 200-week MA visibility for a stock."""
    with get_db() as conn:
        conn.execute(
            "UPDATE stocks SET show_ma = ? WHERE id = ?",
            (1 if show else 0, stock_id),
        )


def save_prices(stock_id: int, df: pd.DataFrame):
    """Save price data. df must have columns: date, close."""
    with get_db() as conn:
        for _, row in df.iterrows():
            conn.execute(
                "INSERT OR REPLACE INTO prices (stock_id, date, close) VALUES (?, ?, ?)",
                (stock_id, str(row["date"]), float(row["close"])),
            )


def get_prices(stock_id: int) -> pd.DataFrame:
    """Load cached price data for a stock."""
    with get_db() as conn:
        df = pd.read_sql_query(
            "SELECT date, close FROM prices WHERE stock_id = ? ORDER BY date",
            conn,
            params=(stock_id,),
        )
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
        return df


def get_last_price_date(stock_id: int) -> str | None:
    """Return the most recent cached date for a stock, or None."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT MAX(date) FROM prices WHERE stock_id = ?",
            (stock_id,),
        ).fetchone()
        return row[0] if row and row[0] else None


def get_alert_state(stock_id: int) -> dict | None:
    """Get alert tracking state for a stock."""
    with get_db() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM alerts WHERE stock_id = ?", (stock_id,)
        ).fetchone()
        return dict(row) if row else None


def update_alert_state(stock_id: int, was_below_ma: bool, alert_date: str | None = None):
    """Update alert state after checking."""
    with get_db() as conn:
        if alert_date:
            conn.execute(
                "UPDATE alerts SET was_below_ma = ?, last_alert_date = ? WHERE stock_id = ?",
                (1 if was_below_ma else 0, alert_date, stock_id),
            )
        else:
            conn.execute(
                "UPDATE alerts SET was_below_ma = ? WHERE stock_id = ?",
                (1 if was_below_ma else 0, stock_id),
            )
