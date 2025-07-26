
import os
import requests
import time
from flask import Flask

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
COINEX_API = "https://api.coinex.com/v1/market/kline"

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

def fetch_klines(market):
    params = {
        "market": market,
        "type": "15min",
        "limit": 30
    }
    try:
        res = requests.get(COINEX_API, params=params).json()
        return res["data"]["klines"]
    except:
        return []

def check_fake_breakout(candles):
    lows = [float(c.split(',')[3]) for c in candles]
    closes = [float(c.split(',')[4]) for c in candles]
    support = min(lows[:-1])
    return float(candles[-1].split(',')[3]) < support and float(candles[-1].split(',')[4]) > support

def check_compression_breakout(candles):
    highs = [float(c.split(',')[2]) for c in candles]
    lows = [float(c.split(',')[3]) for c in candles]
    closes = [float(c.split(',')[4]) for c in candles]
    opens = [float(c.split(',')[1]) for c in candles]
    vols = [float(c.split(',')[5]) for c in candles]

    price_range = max(highs) - min(lows)
    is_tight = price_range / min(lows) < 0.01
    breakout = closes[-1] > max(highs[:-1])
    bullish = closes[-1] > opens[-1]
    vol_ok = vols[-1] > sum(vols) / len(vols)

    return is_tight and breakout and bullish and vol_ok

def check_time_gap_breakout(candles):
    from datetime import datetime
    now = datetime.utcnow()
    if now.hour != 10 and now.hour != 14:
        return False

    highs = [float(c.split(',')[2]) for c in candles]
    closes = [float(c.split(',')[4]) for c in candles]
    opens = [float(c.split(',')[1]) for c in candles]
    vols = [float(c.split(',')[5]) for c in candles]

    prev_high = max(highs[:-1])
    return closes[-1] > prev_high and closes[-1] > opens[-1] and vols[-1] > sum(vols) / len(vols)

def main():
    market_list_url = "https://api.coinex.com/v1/market/list"
    res = requests.get(market_list_url).json()
    usdt_pairs = [pair for pair in res["data"] if pair.endswith("USDT")]

    for pair in usdt_pairs:
        candles = fetch_klines(pair)
        if len(candles) < 20:
            continue

        if check_fake_breakout(candles) or check_compression_breakout(candles) or check_time_gap_breakout(candles):
            send_telegram_alert(f"🚨 Buy Signal on {pair}")

@app.route('/')
def home():
    return "Bot is running!"

if __name__ == '__main__':
    while True:
        try:
            main()
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(300)
