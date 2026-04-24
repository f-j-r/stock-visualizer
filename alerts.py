"""Telegram alerts for 200-week MA crossings and background scheduling."""

import logging
from datetime import datetime

import requests

import config
import db
import data as data_module

logger = logging.getLogger(__name__)


def send_telegram_message(message: str) -> bool:
    """Send a message via Telegram bot API."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured, skipping alert")
        return False

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error("Failed to send Telegram message: %s", e)
        return False


def check_alerts():
    """Check all stocks for 200-week MA crossings and send alerts."""
    logger.info("Checking alerts...")

    # First, refresh all prices
    data_module.update_all_stocks()

    stocks = db.get_stocks()
    for stock in stocks:
        prices = db.get_prices(stock["id"])
        if prices.empty or len(prices) < 200:
            continue

        prices = data_module.compute_200_week_ma(prices)
        latest = prices.iloc[-1]
        current_price = latest["close"]
        ma_value = latest["200_week_ma"]
        # Threshold: 0 = exactly MA, +10 = 10% above MA, -10 = 10% below MA
        threshold = config.ALERT_THRESHOLD_PERCENT
        trigger_level = ma_value * (1 + threshold / 100)
        is_below = current_price < trigger_level

        alert_state = db.get_alert_state(stock["id"])
        was_below = bool(alert_state and alert_state["was_below_ma"])

        # Alert on transition: was above → now below threshold
        if is_below and not was_below:
            if threshold == 0:
                level_desc = "200-week MA"
            elif threshold > 0:
                level_desc = f"{threshold:+.0f}% above 200-week MA"
            else:
                level_desc = f"{threshold:+.0f}% below 200-week MA"
            message = (
                f"⚠️ <b>{stock['display_name']}</b> ({stock['ticker']})\n"
                f"Price ({current_price:.2f}) dropped below {level_desc} ({trigger_level:.2f})"
            )
            send_telegram_message(message)
            db.update_alert_state(
                stock["id"],
                was_below_ma=True,
                alert_date=datetime.now().isoformat(),
            )
            logger.info("Alert sent for %s", stock["display_name"])
        else:
            db.update_alert_state(stock["id"], was_below_ma=is_below)


def setup_scheduler(app):
    """Add a background scheduler to the Dash/Flask app."""
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        check_alerts,
        "interval",
        hours=config.ALERT_CHECK_INTERVAL_HOURS,
        id="alert_checker",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Alert scheduler started (every %d hours)", config.ALERT_CHECK_INTERVAL_HOURS)
