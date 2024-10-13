import logging
import os
from collections import defaultdict
from datetime import datetime
from enum import StrEnum
from typing import Iterable
from urllib.parse import urlencode

import dateutil.parser
import httpx
import trio
from discord import SyncWebhook
from stock_indicators import indicators
from stock_indicators.indicators.common.quote import Quote

import settings

logger = logging.getLogger(__name__)


class Color(StrEnum):
    BOLD = "\033[1m"
    ENDC = "\033[0m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"


class TimeFrame(StrEnum):
    W = "W"
    D = "D"
    H4 = "H4"
    H1 = "H1"
    M15 = "M15"


def configure_logger():
    filename = "incrementum.log"

    root = logging.getLogger()

    formatter = logging.Formatter("{asctime} {name:20s} {levelname:8s} {message}", style="{")

    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    ch.setFormatter(formatter)
    root.addHandler(ch)

    fh = logging.FileHandler(filename)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    root.addHandler(fh)


async def fetch_candles(ccy_pair: str, time_frame: str, count: int = 100) -> Iterable[Quote]:
    endpoint = f"/v3/instruments/{ccy_pair}/candles"
    query_params = {
        "granularity": time_frame,
        "count": count,
    }
    url = f"{settings.OANDA_API_BASE_URL}{endpoint}?{urlencode(query_params)}"
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"authorization": f"Bearer {settings.OANDA_API_ACCESS_TOKEN}"},
            timeout=httpx.Timeout(30, connect=5),
        )
    try:
        response.raise_for_status()
    except httpx.HTTPError as ex:
        logger.error("HTTP Exception for %s - %s", ex.request.url, ex)

    response_json = response.json()
    return (
        Quote(
            date=dateutil.parser.parse(candle["time"]),
            open=candle["mid"]["o"],
            high=candle["mid"]["h"],
            low=candle["mid"]["l"],
            close=candle["mid"]["c"],
            volume=candle["volume"],
        ) for candle in response_json["candles"]
    )


async def main():
    configure_logger()

    async def producer(
        channel: trio.MemorySendChannel,
        ccy_pair: str,
        time_frame: str,
    ):
        async with channel:
            candles = await fetch_candles(ccy_pair, time_frame)
            await channel.send(
                {
                    "ccy_pair": ccy_pair,
                    "time_frame": time_frame,
                    "candles": candles,
                }
            )

    async def consumer(channel: trio.MemoryReceiveChannel):
        stats = defaultdict(lambda: defaultdict(dict))

        async with channel:
            async for data in channel:
                rsi = indicators.get_rsi(data["candles"], lookback_periods=13)[-1].rsi
                stats["rsi"][data["ccy_pair"]][data["time_frame"]] = {
                    "value": rsi,
                    "overbought": True if rsi >= settings.INDICATOR_THRESHOLD["rsi"]["overbought"] else False,
                    "oversold": True if rsi <= settings.INDICATOR_THRESHOLD["rsi"]["oversold"] else False,
                }

        async with httpx.AsyncClient() as client:
            response = await client.get("http://worldtimeapi.org/api/timezone/Australia/Adelaide")
        response.raise_for_status()
        response_json = response.json()
        now = dateutil.parser.parse(response_json["datetime"])

        discord_webhook = SyncWebhook.from_url(settings.DISCORD_WEBHOOK_URL)

        os.system("clear")
        for indicator, indicator_data in stats.items():
            print(37 * "-" + Color.BOLD + f" {indicator.upper()} " + Color.ENDC + 38 * "-")
            print(8 * " ", end="")
            for _time_frame in TimeFrame:
                print(f"| {_time_frame.value:>8s} ", end="")
            print("\n", end="")
            for _ccy_pair in settings.CCY_PAIRS:
                _ccy_pair_data = indicator_data[_ccy_pair]
                overbought_count = 0
                oversold_count = 0
                print(f"{_ccy_pair} ", end="")
                for _time_frame in TimeFrame:
                    indicator_value = _ccy_pair_data[_time_frame]["value"]
                    indicator_overbought = _ccy_pair_data[_time_frame]["overbought"]
                    indicator_oversold = _ccy_pair_data[_time_frame]["oversold"]
                    if indicator_overbought:
                        overbought_count += 1
                    if indicator_oversold:
                        oversold_count += 1
                    print("| ", end="")
                    if indicator_overbought:
                        print(Color.RED + f"{indicator_value: 8.4f}" + Color.ENDC + " ", end="")
                    elif indicator_oversold:
                        print(Color.GREEN + f"{indicator_value: 8.4f}" + Color.ENDC + " ", end="")
                    else:
                        print(f"{indicator_value: 8.4f} ", end="")
                print("\n", end="")

                if settings.DISCORD_NOTIFICATION_ENABLED:
                    if overbought_count >= 3:
                        discord_webhook.send(
                            f"{_ccy_pair} OVERBOUGHT\n"
                            f"    W: {_ccy_pair_data['W']['overbought']} [{_ccy_pair_data['W']['value']: 8.4f}]\n"
                            f"    D: {_ccy_pair_data['D']['overbought']} [{_ccy_pair_data['D']['value']: 8.4f}]\n"
                            f"   H4: {_ccy_pair_data['H4']['overbought']} [{_ccy_pair_data['H4']['value']: 8.4f}]\n"
                            f"   H1: {_ccy_pair_data['H1']['overbought']} [{_ccy_pair_data['H1']['value']: 8.4f}]\n"
                            f"  M15: {_ccy_pair_data['M15']['overbought']} [{_ccy_pair_data['M15']['value']: 8.4f}]\n"
                        )
                    if oversold_count >= 3:
                        discord_webhook.send(
                            f"{_ccy_pair} OVERSOLD\n"
                            f"    W: {_ccy_pair_data['W']['oversold']} [{_ccy_pair_data['W']['value']: 8.4f}]\n"
                            f"    D: {_ccy_pair_data['D']['oversold']} [{_ccy_pair_data['D']['value']: 8.4f}]\n"
                            f"   H4: {_ccy_pair_data['H4']['oversold']} [{_ccy_pair_data['H4']['value']: 8.4f}]\n"
                            f"   H1: {_ccy_pair_data['H1']['oversold']} [{_ccy_pair_data['H1']['value']: 8.4f}]\n"
                            f"  M15: {_ccy_pair_data['M15']['oversold']} [{_ccy_pair_data['M15']['value']: 8.4f}]\n"
                        )

            print("\n", end="")
        print(f"Last updated: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    while True:
        async with trio.open_nursery() as nursery:
            send_channel, receive_channel = trio.open_memory_channel(0)
            async with send_channel, receive_channel:
                for ccy_pair in settings.CCY_PAIRS:
                    for time_frame in (
                        TimeFrame.M15,
                        TimeFrame.H1,
                        TimeFrame.H4,
                        TimeFrame.D,
                        TimeFrame.W,
                    ):
                        nursery.start_soon(producer, send_channel.clone(), ccy_pair, time_frame)

                nursery.start_soon(consumer, receive_channel.clone())

        await trio.sleep(settings.POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    trio.run(main)
