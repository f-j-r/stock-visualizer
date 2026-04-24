"""Application configuration via environment variables."""

import os

DB_PATH = os.getenv("SV_DB_PATH", "data/stocks.db")
TELEGRAM_BOT_TOKEN = os.getenv("SV_TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("SV_TELEGRAM_CHAT_ID", "")
ALERT_CHECK_INTERVAL_HOURS = int(os.getenv("SV_ALERT_CHECK_HOURS", "4"))
ALERT_THRESHOLD_PERCENT = float(os.getenv("SV_ALERT_THRESHOLD_PERCENT", "0"))
HOST = os.getenv("SV_HOST", "0.0.0.0")
PORT = int(os.getenv("SV_PORT", "8050"))
DEBUG = os.getenv("SV_DEBUG", "false").lower() == "true"
