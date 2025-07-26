import time
import requests
import hmac
import hashlib
import base64
import json
from datetime import datetime
import threading

# ========== الإعدادات ==========
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

COINEX_API_URL = "https://api.coinex.com/v1/market/ticker/all"
INTERVAL_SECONDS = 300  # كل 5 دقائق

LOOKBACK = 20

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram Error: {e}")

def fetch_market_data():
    try:
        res = requests.get(COINEX_API_URL)
        data = res.json()
        return data["data"]["ticker"]
    except Exception as e:
        print(f"API Error: {e}")
        return {}

def check_fake_breakout(candles):
    lows = [float(c["low"]) for c in candles]
    closes = [float(c["close"]) for c in candles]
    current_low = lows[-1]
    current_close = closes[-1]
    support = min(lows[-LOOKBACK:])
    return current_low < support and current_close > support

def check_compression_breakout(candles):
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    closes = [float(c["close"]) for c in candles]
    opens = [float(c["open"]) for c in candles]
    volumes = [float(c["volume"]) for c in candles]
    current_close = closes[-1]
    current_open = opens[-1]
    price_range = max(highs[-LOOKBACK:]) - min(lows[-LOOKBACK:])
    is_tight = price_range / min(lows[-LOOKBACK:]) < 0.01
    breakout = current_close > max(highs[-LOOKBACK:-1])
    avg_volume = sum(volumes[-LOOKBACK:]) / LOOKBACK
    return is_tight and breakout and current_close > current_open and volumes[-1] > avg_volume

def check_price_gap_entry(candles):
    hours_to_check = [10, 14]
    now = datetime.utcnow()
    current_hour = now.hour
    if current_hour not in hours_to_check:
        return False
    highs = [float(c["high"]) for c in candles]
    closes = [float(c["close"]) for c in candles]
    opens = [float(c["open"]) for c in candles]
    volumes = [float(c["volume"]) for c in candles]
    prev_high = max(highs[-LOOKBACK-1:-1])
    breakout = closes[-1] > prev_high
    avg_volume = sum(volumes[-LOOKBACK:]) / LOOKBACK
    return breakout and closes[-1] > opens[-1] and volumes[-1] > avg_volume

def get_klines(symbol):
    url = f"https://api.coinex.com/v1/market/kline?market={symbol}&type=15min&limit={LOOKBACK+1}"
    try:
        res = requests.get(url)
        candles = res.json()["data"]
        return [{"open": i[1], "high": i[3], "low": i[4], "close": i[2], "volume": i[5]} for i in candles]
    except:
        return []

def run_bot():
    while True:
        print("Scanning...")
        data = fetch_market_data()
        for symbol in data:
            if not symbol.endswith("USDT"):
                continue
            candles = get_klines(symbol)
            if len(candles) < LOOKBACK + 1:
                continue
            if (
                check_fake_breakout(candles)
                or check_compression_breakout(candles)
                or check_price_gap_entry(candles)
            ):
                send_telegram_message(f"📢 فرصة على: {symbol}")
                time.sleep(1)
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    run_bot()