import time
import logging
import csv
import os
from datetime import datetime, timedelta

from scanner_logic import build_signal
from binance_client import get_usdt_symbols
from telegram_bot import send_alert
from keep_alive import keep_alive

from config import (
    SCAN_INTERVAL_SECONDS,
    MIN_ALERT_INTERVAL_MINUTES,
)

logging.basicConfig(level=logging.INFO)

last_alert_times = {}
ping_state = {}  # { symbol: {"count": int, "start": datetime} }

LOG_FILE = "signals_log.csv"


# ===============================
#  Log file helpers
# ===============================
def init_log_file():
    """إنشاء ملف CSV مع الهيدر لو مش موجود."""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp_utc",
                "symbol",
                "side",
                "grade",
                "score",
                "price",
                "rsi_15m",
                "rsi_1h",
                "change_24h_percent",
                "quote_volume_24h",
                "vol_1m",
                "vol_5m",
                "vol_15m",
                "vol_60m",
                "net_vol_1m",
                "net_vol_15m",
                "net_vol_60m",
                "ping_count_24h",
            ])


def log_signal(sig: dict):
    """تسجيل الإشارة في ملف CSV."""
    try:
        timestamp = datetime.utcnow().isoformat()
        sym = sig.get("symbol", "")
        side = sig.get("side", "BUY")
        grade = sig.get("grade", "")
        score = sig.get("score", 0)
        price = sig.get("price", 0.0)
        rsi_15m = sig.get("rsi_now", 0.0)
        rsi_1h = sig.get("rsi_1h", 0.0)
        change_24h = sig.get("change_24h", 0.0)
        qv_24h = sig.get("quote_volume_24h", 0.0)

        vol_1m = sig.get("vol_1m", 0.0)
        vol_5m = sig.get("vol_5m", 0.0)
        vol_15m = sig.get("vol_15m", 0.0)
        vol_60m = sig.get("vol_60m", 0.0)

        net_vol_1m = sig.get("net_vol_1m", 0.0)
        net_vol_15 = sig.get("net_vol_15", 0.0)
        net_vol_60 = sig.get("net_vol_60", 0.0)

        ping_count = sig.get("ping_count", 0)

        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                sym,
                side,
                grade,
                score,
                price,
                rsi_15m,
                rsi_1h,
                change_24h,
                qv_24h,
                vol_1m,
                vol_5m,
                vol_15m,
                vol_60m,
                net_vol_1m,
                net_vol_15,
                net_vol_60,
                ping_count,
            ])
    except Exception as e:
        logging.error(f"Error logging signal: {e}")


# ===============================
#  Alert timing
# ===============================
def should_alert(symbol: str) -> bool:
    now = datetime.utcnow()
    last_time = last_alert_times.get(symbol)

    if last_time is None:
        return True

    if now - last_time >= timedelta(minutes=MIN_ALERT_INTERVAL_MINUTES):
        return True

    return False


def record_alert(symbol: str):
    last_alert_times[symbol] = datetime.utcnow()


# ===============================
#  Ping logic
# ===============================
def update_ping(symbol: str, net_vol_1m: float, quote_vol_24h: float) -> int:
    """
    Ping:
    - net_vol_1m > 0.3% من حجم تداول 24 ساعة
    - كل مرة يتحقق الشرط → نزود عدد الـ pings للعملة خلال آخر 24 ساعة
    - بعد 24 ساعة من أول ping → العداد يُعاد من جديد
    """
    if quote_vol_24h <= 0 or net_vol_1m <= 0:
        return ping_state.get(symbol, {}).get("count", 0)

    threshold = 0.003 * quote_vol_24h  # 0.3%
    if net_vol_1m <= threshold:
        return ping_state.get(symbol, {}).get("count", 0)

    now = datetime.utcnow()
    info = ping_state.get(symbol)

    if not info or now - info["start"] >= timedelta(hours=24):
        ping_state[symbol] = {"count": 1, "start": now}
    else:
        ping_state[symbol]["count"] += 1

    return ping_state[symbol]["count"]


# ===============================
#  UI helpers
# ===============================
def build_header_by_grade(grade: str, base: str, side: str) -> str:
    if "Very Strong" in grade:
        line = "🟢🟢🟢 *VERY STRONG SIGNAL* 🟢🟢🟢"
    elif "Strong" in grade:
        line = "🟧🟧 *STRONG SIGNAL* 🟧🟧"
    elif "Good" in grade:
        line = "🔵 *GOOD SIGNAL* 🔵"
    else:
        line = "⚪ *WEAK SIGNAL* ⚪"

    title_base = f"{base} {side} signal"
    return f"{line}\n*{title_base.upper()}*"


def format_msg(sig):
    sym = sig["symbol"]

    if sym.endswith("USDT"):
        base = sym[:-4]
    else:
        base = sym

    price = sig["price"]
    grade = sig["grade"]
    score = sig["score"]
    qv = sig["quote_volume_24h"]
    rsi_now = sig["rsi_now"]
    rsi_min = sig["rsi_min"]
    side = sig.get("side", "BUY")

    vol_1m = sig.get("vol_1m", 0.0)
    vol_5m = sig.get("vol_5m", 0.0)
    vol_15m = sig.get("vol_15m", 0.0)
    vol_60m = sig.get("vol_60m", 0.0)
    net_vol_15 = sig.get("net_vol_15", 0.0)
    net_vol_60 = sig.get("net_vol_60", 0.0)
    ping_count = sig.get("ping_count", 0)

    reasons = "\n".join([f"• {r}" for r in sig["reasons"]])

    separator = "━━━━━━━━━━━━━━━━━━━━"
    header = build_header_by_grade(grade, base, side)

    msg = (
        f"{header}\n"
        f"{separator}\n"
        f"*{base}* (`{sym}`)\n"
        f"#{base}   ${base}\n\n"
        f"🧭 *Signal Type:* `{side}`\n"
        f"📊 *Grade:* {grade}\n"
        f"💰 *Price:* `{price}`\n"
        f"💵 *24h Volume:* `{qv:,.0f}` USDT\n"
        f"📉 *RSI 15m:* `{rsi_now:.1f}` (Min {rsi_min:.1f})\n"
        f"⭐ *Score:* `{score}`\n"
        f"📌 *Pings (24h):* `{ping_count}`\n\n"
        f"🔊 *Vol 1m / 5m / 15m / 60m:*\n"
        f"`{vol_1m:,.0f}` / `{vol_5m:,.0f}` / `{vol_15m:,.0f}` / `{vol_60m:,.0f}`\n"
        f"📈 *Net Vol 15m / 60m:* `{net_vol_15:,.0f}` / `{net_vol_60:,.0f}`\n\n"
        f"*Reasons:*\n{reasons}\n\n"
        f"[فتح الشارت على TradingView](https://www.tradingview.com/chart/?symbol=BINANCE:{sym})"
    )

    return msg


# ===============================
#  Main loop
# ===============================
def main_loop():
    while True:
        logging.info("Starting scan...")
        symbols = get_usdt_symbols()

        for sym in symbols:
            try:
                sig = build_signal(sym)
                if not sig:
                    continue

                # 🚫 فلتر: تجاهل إشارات Weak تمامًا
                grade = sig.get("grade", "")
                if "Weak" in grade:
                    continue

                # حساب الـ Ping لكل عملة بناءً على net_vol_1m و 24h volume
                net_vol_1m = sig.get("net_vol_1m", 0.0)
                qv_24h = sig.get("quote_volume_24h", 0.0)
                ping_count = update_ping(sym, net_vol_1m, qv_24h)
                sig["ping_count"] = ping_count

                if should_alert(sym):
                    # نسجّل الإشارة في CSV
                    log_signal(sig)

                    # نرسلها على تليجرام
                    message = format_msg(sig)
                    send_alert(message)
                    record_alert(sym)
                    logging.info(f"[ALERT SENT] {sym} | pings={ping_count}")

            except Exception as e:
                logging.error(f"Error processing {sym}: {e}")

        logging.info("Scan finished. Sleeping...")
        time.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    init_log_file()
    keep_alive()
    send_alert("🚀 *Advanced Crypto Scanner* is now running on Replit")
    main_loop()
