import logging

from decouple import config

OANDA_API_BASE_URL = "https://api-fxtrade.oanda.com"
OANDA_API_ACCESS_TOKEN = config("OANDA_API_ACCESS_TOKEN", default=None)

CCY_PAIRS = (
    "AUD_CAD",
    "AUD_JPY",
    "AUD_NZD",
    "AUD_USD",
    "AUD_CHF",
    "NZD_CAD",
    "NZD_JPY",
    "NZD_USD",
    "NZD_CHF",
    "GBP_JPY",
    "GBP_USD",
    "GBP_CHF",
)

INDICATOR_THRESHOLD = {
    "rsi": {
        "overbought": 70,
        "oversold": 30,
    },
}

POLL_INTERVAL_SECONDS = 300

DISCORD_NOTIFICATION_ENABLED = True
DISCORD_WEBHOOK_URL = config("DISCORD_WEBHOOK_URL", default=None)
