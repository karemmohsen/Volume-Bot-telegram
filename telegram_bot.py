# telegram_bot.py

import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID


def send_alert(message: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram credentials not set. Skipping send_alert.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, data=data, timeout=10)
        if resp.status_code != 200:
            print("⚠️ Telegram API error:", resp.status_code, resp.text)
        resp.raise_for_status()
    except Exception as e:
        print(f"⚠️ Error sending Telegram alert: {e}")
