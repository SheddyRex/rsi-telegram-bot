import requests
import pandas as pd
import time
import schedule
import os
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

# configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
    'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'MATICUSDT'
]
INTERVAL = '4h'
RSI_PERIOD = 14
EMA_PERIOD = 50
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# === Functions ===
def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"❌ Telegram error: {response.text}")
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")

def get_binance_klines(symbol, interval, limit=200):
    url = f'https://api.binance.com/api/v3/klines'
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
    ])
    df['close'] = df['close'].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def analyze_rsi_for_symbol(symbol):
    try:
        print(f"🔍 Checking {symbol}...")
        df = get_binance_klines(symbol, INTERVAL)
        rsi = RSIIndicator(close=df['close'], window=14).rsi()
        ema = EMAIndicator(close=df['close'], window=200).ema_indicator()

        latest = df.iloc[-1]
        rsi = latest['RSI']
        price = latest['close']
        ema = latest['EMA']
        time_str = latest['timestamp']

        if pd.isna(rsi) or pd.isna(ema):
            print(f"⚠️ Not enough data for {symbol}. Skipping.")
            return

        signal = None

        if rsi >= RSI_OVERBOUGHT:
            signal = f'🔴 RSI {rsi:.2f} (Overbought) on {symbol} (4H)\nPrice: ${price:.2f}\nTime: {time_str}'
            if price < ema:
                signal += "\n📉 Below EMA — caution."
        elif rsi <= RSI_OVERSOLD:
            signal = f'🟢 RSI {rsi:.2f} (Oversold) on {symbol} (4H)\nPrice: ${price:.2f}\nTime: {time_str}'
            if price > ema:
                signal += "\n📈 Above EMA — possible bounce."

        if signal:
            print(signal)
            send_telegram_message(signal)
        else:
            print(f"✅ No RSI signal for {symbol}. RSI={rsi:.2f}")

    except Exception as e:
        print(f"❌ Error analyzing {symbol}: {e}")

def analyze_all_symbols():
    print("📊 Starting analysis for all symbols...\n")
    for symbol in SYMBOLS:
        analyze_rsi_for_symbol(symbol)
    print("\n✅ Analysis complete.\n")

# === Scheduler ===
schedule.every(3).minutes.do(analyze_all_symbols)

print("📡 RSI Bot started. Checking every 3 minutes.")
analyze_all_symbols()  # Run once immediately on startup

while True:
    schedule.run_pending()
    time.sleep(1)
