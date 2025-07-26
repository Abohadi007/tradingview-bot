import requests
import os
import time

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
INTERVAL = 900  # 15 دقيقة = 900 ثانية

def send_telegram_alert(symbol, reason):
    message = f"🚨 إشارة شراء على {symbol}\nالسبب: {reason}"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except:
        pass

def get_symbols():
    try:
        res = requests.get("https://api.coinex.com/v1/market/list")
        data = res.json()
        return [s for s in data["data"] if s.endswith("USDT")]
    except:
        return []

def get_klines(symbol):
    url = f"https://api.coinex.com/v1/market/kline?market={symbol}&type=15min&limit=25"
    try:
        res = requests.get(url)
        return res.json()["data"]
    except:
        return []

def check_fake_breakout(candles):
    lows = [c[3] for c in candles[-20:]]
    support = min(lows)
    broke_below = candles[-1][3] < support
    closed_above = candles[-1][2] > support
    return broke_below and closed_above

def check_compression_breakout(candles):
    highs = [c[1] for c in candles[-20:]]
    lows = [c[3] for c in candles[-20:]]
    price_range = max(highs) - min(lows)
    is_tight = price_range / min(lows) < 0.01
    breakout = candles[-1][2] > max(highs[:-1])
    green = candles[-1][2] > candles[-1][1]
    volumes = [c[5] for c in candles[-20:]]
    vol_check = candles[-1][5] > sum(volumes)/len(volumes)
    return is_tight and breakout and green and vol_check

def check_time_gap_breakout(candles):
    from datetime import datetime
    timestamp = candles[-1][0]
    hour = datetime.utcfromtimestamp(timestamp).hour
    if hour not in [10, 14]: return False
    highs = [c[1] for c in candles[-21:-1]]
    prev_high = max(highs)
    breakout = candles[-1][2] > prev_high
    green = candles[-1][2] > candles[-1][1]
    volumes = [c[5] for c in candles[-20:]]
    vol_check = candles[-1][5] > sum(volumes)/len(volumes)
    return breakout and green and vol_check

def main():
    while True:
        symbols = get_symbols()
        for sym in symbols:
            candles = get_klines(sym)
            if len(candles) < 21:
                continue
            if check_fake_breakout(candles):
                send_telegram_alert(sym, "كسر كاذب")
            elif check_compression_breakout(candles):
                send_telegram_alert(sym, "ضغط + شمعة")
            elif check_time_gap_breakout(candles):
                send_telegram_alert(sym, "فجوة زمنية")
            time.sleep(1)
        time.sleep(60)

if __name__ == "__main__":
    main()