# binance_client.py

import requests
from typing import List, Dict
from config import BINANCE_BASE_URL


def get_usdt_symbols() -> List[str]:
    """
    يرجّع كل أزواج USDT المتاحة على Binance Spot.
    """
    url = f"{BINANCE_BASE_URL}/api/v3/exchangeInfo"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    symbols = []
    for s in data["symbols"]:
        if s["quoteAsset"] == "USDT" and s["status"] == "TRADING":
            symbols.append(s["symbol"])
    return symbols


def get_klines(symbol: str, interval: str, limit: int) -> List[Dict]:
    """
    يرجّع شموع لرمز معيّن.
    """
    url = f"{BINANCE_BASE_URL}/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    raw_klines = resp.json()

    klines = []
    for k in raw_klines:
        klines.append({
            "open_time": k[0],
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
            "close_time": k[6],
        })
    return klines


def get_24h_ticker(symbol: str) -> Dict:
    """
    بيانات 24 ساعة (منها الحجم).
    """
    url = f"{BINANCE_BASE_URL}/api/v3/ticker/24hr"
    params = {"symbol": symbol}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()
