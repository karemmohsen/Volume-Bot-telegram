# keep_alive.py

from flask import Flask
import threading

app = Flask(__name__)


@app.route("/")
def home():
    return "🚀 Crypto scanner is running!"


def run():
    # Replit بيفتح السيرفر على 0.0.0.0:8080
    app.run(host="0.0.0.0", port=8080)


def keep_alive():
    """
    تشغيل السيرفر في Thread منفصل علشان main_loop يفضل شغال.
    """
    t = threading.Thread(target=run)
    t.daemon = True
    t.start()
