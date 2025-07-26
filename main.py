import requests
import time
import os
from datetime import datetime

COINEX_API_URL = "https://api.coinex.com/v1/market/ticker/all"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

LOOKBACK = 20
CHECK_INTERVAL = 60  # seconds

def fetch_data():
    try:
        response = requests.get(COINEX_API_URL)
        return response.json()["data"]["ticker"]
    except:
        return {}

def fake_breakout(data):
    lows = [float(c["low"]) for c in data]
    support = min(lows[-LOOKBACK:])
    return float(data[-1]["low"]) < support and float(data[-1]["close"]) > support

def compression_breakout(data):
    highs = [float(c["high"]) for c in data]
    lows = [float(c["low"]) for c in data]
    price_range = max(highs[-LOOKBACK:]) - min(lows[-LOOKBACK:])
    tight = price_range / min(lows[-LOOKBACK:]) < 0.01
    breakout = float(data[-1]["close"]) > max(highs[-LOOKBACK-1:-1])
    return tight and breakout and float(data[-1]["close"]) > float(data[-1]["open"])

def time_condition():
    hour = datetime.utcnow().hour + 3  # UTC+3
    return hour in [10, 14]

def time_gap_entry(data):
    highs = [float(c["high"]) for c in data]
    prev_high = max(highs[-LOOKBACK-1:-1])
    breakout = float(data[-1]["close"]) > prev_high
    return breakout and time_condition() and float(data[-1]["close"]) > float(data[-1]["open"])

def send_alert(symbol, reason):
    msg = f"🚨 فرصة على {symbol}\nالسبب: {reason}"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    requests.post(url, data=data)

def main():
    print("Bot started...")
    while True:
        tickers = fetch_data()
        for symbol, info in tickers.items():
            if not symbol.endswith("USDT"):
                continue
            try:
                klines_url = f"https://api.coinex.com/v1/market/kline?market={symbol}&type=15min&limit=LOOKBACK"
                res = requests.get(klines_url).json()
                candles = [{"open": x[1], "high": x[3], "low": x[4], "close": x[2]} for x in res["data"]]

                if fake_breakout(candles):
                    send_alert(symbol, "كسر كاذب")
                elif compression_breakout(candles):
                    send_alert(symbol, "ضغط + شمعة")
                elif time_gap_entry(candles):
                    send_alert(symbol, "فجوة زمنية")
            except:
                continue
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()