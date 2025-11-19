import os

# ======================
# Binance Endpoints
# ======================
BINANCE_BASE_URL = "https://data-api.binance.vision"

# ======================
# Timeframes
# ======================
KLINE_INTERVAL = "15m"      # Main timeframe
FAST_INTERVAL = "5m"        # Fast confirmation
SLOW_INTERVAL = "1h"        # Trend timeframe

KLINE_LIMIT = 80

# ======================
# Liquidity / Volume Filters
# ======================
MIN_24H_VOLUME_USDT = 1_000_000   # حد أدنى لحجم التداول 24h

MAIN_VOLUME_WINDOW = 20
FAST_VOLUME_WINDOW = 10

MAIN_VOLUME_SPIKE_MULTIPLIER = 3.0
FAST_VOLUME_SPIKE_MULTIPLIER = 2.0

# ======================
# Breakout
# ======================
BREAKOUT_LOOKBACK = 20

# ======================
# RSI Settings (15m)
# ======================
RSI_PERIOD = 14
RSI_RECENT_LOOKBACK = 20
RSI_MIN_BEFORE = 40.0
RSI_NOW_MIN = 45.0
RSI_NOW_MAX = 70.0

# ======================
# Trend (EMA) on 1h
# ======================
EMA_FAST_PERIOD = 20
EMA_SLOW_PERIOD = 50

# ======================
# Extra Safety Filters (over-extension)
# ======================

# أقصى تغيير مسموح به في 24 ساعة
MAX_24H_POS_CHANGE = 25.0    # +25% كحد أقصى
MAX_24H_NEG_CHANGE = -10.0   # ما تكونش نازلة أكتر من -10%

# أقصى RSI على فريم الساعة
MAX_1H_RSI = 70.0

# أقصى بُعد للسعر عن EMA50 على فريم الساعة
MAX_TREND_EXTENSION = 0.08   # 8%

# ======================
# Net Volume Windows
# ======================
# عدد الشموع المستخدمة لحساب net volume (جَمْع أحجام الشموع الخضراء - الحمراء)
NET_VOLUME_WINDOW_15 = 4   # آخر 4 شمعات 15m ≈ ساعة
NET_VOLUME_WINDOW_60 = 4   # آخر 4 شمعات 1h ≈ 4 ساعات

# ======================
# Scanner Interval
# ======================
SCAN_INTERVAL_SECONDS = 300       # run every 5 min
MIN_ALERT_INTERVAL_MINUTES = 60   # لا يرسل نفس العملة مرتين في ساعة

# ======================
# Telegram
# ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
