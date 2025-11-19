from typing import Optional, Dict, List, Tuple
from statistics import mean

from config import (
    KLINE_INTERVAL,
    KLINE_LIMIT,
    FAST_INTERVAL,
    SLOW_INTERVAL,
    MIN_24H_VOLUME_USDT,
    MAIN_VOLUME_WINDOW,
    FAST_VOLUME_WINDOW,
    MAIN_VOLUME_SPIKE_MULTIPLIER,
    FAST_VOLUME_SPIKE_MULTIPLIER,
    BREAKOUT_LOOKBACK,
    RSI_PERIOD,
    RSI_RECENT_LOOKBACK,
    RSI_MIN_BEFORE,
    RSI_NOW_MIN,
    RSI_NOW_MAX,
    EMA_FAST_PERIOD,
    EMA_SLOW_PERIOD,
    MAX_24H_POS_CHANGE,
    MAX_24H_NEG_CHANGE,
    MAX_1H_RSI,
    MAX_TREND_EXTENSION,
    NET_VOLUME_WINDOW_15,
    NET_VOLUME_WINDOW_60,
)

from binance_client import get_klines, get_24h_ticker


# ===================================================
# EMA
# ===================================================
def ema(values: List[float], period: int) -> float:
    if len(values) < period:
        return mean(values)
    k = 2 / (period + 1)
    ema_val = mean(values[:period])
    for v in values[period:]:
        ema_val = (v * k) + (ema_val * (1 - k))
    return ema_val


# ===================================================
# RSI
# ===================================================
def rsi(values: List[float], period: int) -> float:
    if len(values) <= period:
        return 50.0

    gains = []
    losses = []
    for i in range(1, period + 1):
        diff = values[-i] - values[-i - 1]
        if diff >= 0:
            gains.append(diff)
        else:
            losses.append(-diff)

    avg_gain = mean(gains) if gains else 0.0
    avg_loss = mean(losses) if losses else 0.0

    if avg_loss == 0:
        return 70.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# ===================================================
# Volume spike
# ===================================================
def volume_spike(volumes: List[float], window: int) -> float:
    if len(volumes) <= window:
        return 0
    last = volumes[-1]
    prev = volumes[-(window + 1):-1]
    if mean(prev) == 0:
        return 0
    return last / mean(prev)


# ===================================================
# Breakout check
# ===================================================
def is_breakout(highs: List[float], closes: List[float], lookback: int) -> bool:
    if len(highs) < lookback + 2:
        return False
    last_close = closes[-1]
    prev_high = max(highs[-(lookback + 1):-1])
    return last_close > prev_high


# ===================================================
# Candle strength
# ===================================================
def bull_strength(open_p, high, low, close) -> float:
    if high == low:
        return 0.5
    body = abs(close - open_p)
    rng = high - low
    body_ratio = body / rng
    close_ratio = (close - low) / rng
    return (body_ratio + close_ratio) / 2


# ===================================================
# Net Volume (green - red volumes)
# ===================================================
def net_volume(klines: List[Dict], window: int) -> float:
    if not klines:
        return 0.0
    window = min(window, len(klines))
    total = 0.0
    for k in klines[-window:]:
        v = k["volume"]
        if k["close"] >= k["open"]:
            total += v
        else:
            total -= v
    return total


# ===================================================
# 24h volume + change filters
# ===================================================
def liquidity_and_change(symbol: str) -> Tuple[bool, float, float]:
    """
    يرجّع:
    - هل السيولة كافية؟
    - حجم تداول 24h
    - نسبة التغيير في السعر خلال 24h
    """
    ticker = get_24h_ticker(symbol)
    qv = float(ticker.get("quoteVolume", 0))
    change_pct = float(ticker.get("priceChangePercent", 0))
    enough = qv >= MIN_24H_VOLUME_USDT

    # فلتر: لا نريد عملة already طايرة بقوة أو منهارة بعنف
    if change_pct > MAX_24H_POS_CHANGE or change_pct < MAX_24H_NEG_CHANGE:
        return False, qv, change_pct

    return enough, qv, change_pct


def small_uptrend_score(closes: List[float], lookback: int = 5) -> int:
    """
    يحسب عدد الشموع الصاعدة في آخر N شمعة،
    عشان نتأكد إن في اتجاه معقول، مش فجأة شمعة مجنونة واحدة.
    """
    score = 0
    if len(closes) < lookback + 1:
        return 0
    for i in range(1, lookback + 1):
        if closes[-i] > closes[-i - 1]:
            score += 1
    return score


# ===================================================
# Main Signal Builder
# ===================================================
def build_signal(symbol: str) -> Optional[Dict]:
    # ---------------------------
    # Liquidity + 24h change
    # ---------------------------
    enough, qv, change_pct = liquidity_and_change(symbol)
    if not enough:
        return None

    # ---------------------------
    # Main 15m data
    # ---------------------------
    m = get_klines(symbol, KLINE_INTERVAL, KLINE_LIMIT)
    closes = [k["close"] for k in m]
    highs = [k["high"] for k in m]
    lows = [k["low"] for k in m]
    vols_15 = [k["volume"] for k in m]

    last = m[-1]
    last_close = last["close"]

    # Volume spike 15m
    main_spike = volume_spike(vols_15, MAIN_VOLUME_WINDOW)
    cond_main_spike = main_spike >= MAIN_VOLUME_SPIKE_MULTIPLIER

    # Breakout 15m
    cond_breakout = is_breakout(highs, closes, BREAKOUT_LOOKBACK)

    # RSI logic على 15m
    rsi_now = rsi(closes, RSI_PERIOD)
    rsi_hist = [
        rsi(closes[:-i], RSI_PERIOD)
        for i in range(1, RSI_RECENT_LOOKBACK + 2)
        if len(closes) > RSI_PERIOD + i
    ]
    rsi_min_before = min(rsi_hist) if rsi_hist else rsi_now
    cond_rsi = (
        rsi_min_before <= RSI_MIN_BEFORE
        and RSI_NOW_MIN <= rsi_now <= RSI_NOW_MAX
    )

    # mini-uptrend قبل السبايك
    up_score = small_uptrend_score(closes, lookback=5)
    cond_small_uptrend = up_score >= 3  # على الأقل 3 من 5 خضر

    # ---------------------------
    # 5m fast confirmation
    # ---------------------------
    f = get_klines(symbol, FAST_INTERVAL, 40)
    vols_5 = [k["volume"] for k in f]
    f_last = f[-1]

    fast_spike = volume_spike(vols_5, FAST_VOLUME_WINDOW)
    cond_fast_spike = fast_spike >= FAST_VOLUME_SPIKE_MULTIPLIER

    bull_str = bull_strength(f_last["open"], f_last["high"], f_last["low"], f_last["close"])
    cond_bull = f_last["close"] > f_last["open"] and bull_str >= 0.6

    # ---------------------------
    # 1h trend + overextension filters
    # ---------------------------
    h = get_klines(symbol, SLOW_INTERVAL, 80)
    closes_1h = [k["close"] for k in h]
    vols_60 = [k["volume"] for k in h]

    ema_fast = ema(closes_1h, EMA_FAST_PERIOD)
    ema_slow = ema(closes_1h, EMA_SLOW_PERIOD)
    last_h_close = closes_1h[-1]

    # ترند صاعد أساسي
    cond_trend = ema_fast > ema_slow and last_h_close > ema_fast

    # RSI 1h لتجنب overbought
    rsi_1h = rsi(closes_1h, RSI_PERIOD)
    cond_rsi_1h_ok = rsi_1h <= MAX_1H_RSI

    # Extension: بُعد السعر عن EMA50
    ext = (last_h_close - ema_slow) / ema_slow if ema_slow != 0 else 0
    cond_not_overextended = ext <= MAX_TREND_EXTENSION

    # ---------------------------
    # Extra volumes: 1m + net volumes (15m/60m)
    # ---------------------------
    kl_1m = get_klines(symbol, "1m", 20)
    if kl_1m:
        last_1m = kl_1m[-1]
        vol_1m_last = last_1m["volume"]
        # net volume 1m = حجم الشمعة موجب لو خضرا، سالب لو حمرا
        net_vol_1m = vol_1m_last if last_1m["close"] >= last_1m["open"] else -vol_1m_last
    else:
        vol_1m_last = 0.0
        net_vol_1m = 0.0

    vols_1 = [k["volume"] for k in kl_1m] if kl_1m else []
    vol_5m_last = vols_5[-1] if vols_5 else 0.0
    vol_15m_last = vols_15[-1] if vols_15 else 0.0
    vol_60m_last = vols_60[-1] if vols_60 else 0.0

    # Net volume 15m (آخر ساعة تقريباً) و 60m (آخر 4 ساعات)
    net_vol_15 = net_volume(m, NET_VOLUME_WINDOW_15)
    net_vol_60 = net_volume(h, NET_VOLUME_WINDOW_60)

    cond_net_15_pos = net_vol_15 > 0
    cond_net_60_pos = net_vol_60 > 0

    # ---------------------------
    # Score system
    # ---------------------------
    score = 0
    reasons = []

    if cond_main_spike:
        score += 2
        reasons.append(f"Main 15m spike x{main_spike:.2f}")

    if cond_breakout:
        score += 2
        reasons.append("Breakout 15m")

    if cond_rsi:
        score += 1
        reasons.append(f"RSI rebound (min {rsi_min_before:.1f} → {rsi_now:.1f})")

    if cond_fast_spike:
        score += 1
        reasons.append(f"Fast 5m spike x{fast_spike:.2f}")

    if cond_bull:
        score += 1
        reasons.append(f"Strong 5m bullish candle (strength {bull_str:.2f})")

    if cond_small_uptrend:
        score += 1
        reasons.append(f"Short-term uptrend: {up_score}/5 last candles green")

    if cond_trend:
        score += 2
        reasons.append("1h uptrend (EMA20 > EMA50 & price above EMA20)")

    if cond_net_15_pos:
        score += 1
        reasons.append(f"Net volume 15m window positive ({net_vol_15:.0f})")

    if cond_net_60_pos:
        score += 1
        reasons.append(f"Net volume 60m window positive ({net_vol_60:.0f})")

    # فلاتر حماية قوية
    if not cond_rsi_1h_ok:
        return None

    if not cond_not_overextended:
        return None

    if not cond_net_15_pos or not cond_net_60_pos:
        return None

    # لو النتيجة أقل من حد معيّن، ما نبعتش أصلاً
    if score < 6:
        return None

    if score >= 9:
        grade = "🚀 Very Strong"
    elif score >= 8:
        grade = "🔥 Strong"
    elif score == 7:
        grade = "✅ Good"
    else:
        grade = "⚠️ Weak"

    # حاليًا كل الشروط صعودية → إشارة شراء (Long)
    side = "BUY"

    return {
        "symbol": symbol,
        "price": last_close,
        "quote_volume_24h": qv,
        "change_24h": change_pct,
        "main_spike": main_spike,
        "fast_spike": fast_spike,
        "rsi_now": rsi_now,
        "rsi_min": rsi_min_before,
        "rsi_1h": rsi_1h,
        "trend_extension": ext,
        "grade": grade,
        "score": score,
        "reasons": reasons,
        "vol_1m": vol_1m_last,
        "vol_5m": vol_5m_last,
        "vol_15m": vol_15m_last,
        "vol_60m": vol_60m_last,
        "net_vol_1m": net_vol_1m,
        "net_vol_15": net_vol_15,
        "net_vol_60": net_vol_60,
        "side": side,
    }
