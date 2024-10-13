import logging

from decouple import config

OANDA_API_BASE_URL = "https://api-fxtrade.oanda.com"
OANDA_API_ACCESS_TOKEN = config("OANDA_API_ACCESS_TOKEN", default=None)

CCY_PAIRS = (
    "AUD_CAD",
    "AUD_JPY",
    "AUD_NZD",
    "NZD_CAD",
    "NZD_JPY",
    "GBP_JPY",
    "GBP_USD",
)

INDICATOR_THRESHOLD = {
    "rsi": {
        "overbought": 68,
        "oversold": 32,
    },
}

POLL_INTERVAL_SECONDS = 300

DISCORD_NOTIFICATION_ENABLED = True
DISCORD_WEBHOOK_URL = config("DISCORD_WEBHOOK_URL", default=None)
