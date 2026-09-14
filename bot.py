import time
import os
import logging
import json
import collections
import requests
import datetime
import pandas as pd

import exchange_api
import strategy

log_history = collections.deque(maxlen=200)

def json_serialize_helper(obj):
    if hasattr(obj, 'item'):
        return obj.item()
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    return str(obj)

class MemoryHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = record.getMessage()
            if any(ignore in msg for ignore in ["GET /api", "POST /api", "Debugger", "running on http", "127.0.0.1", "is still forming", "Press CTRL+C"]):
                return
            log_entry = self.format(record)
            log_history.append(log_entry)
        except Exception:
            self.handleError(record)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

mem_handler = MemoryHandler()
mem_handler.setFormatter(formatter)
logger.addHandler(mem_handler)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
CONFIG_EXAMPLE_FILE = os.path.join(os.path.dirname(__file__), "config.example.json")
AI_RESULTS_FILE = os.path.join(os.path.dirname(__file__), "latest_ai_results.json")

bot_running = False

def load_config():
    if not os.path.exists(CONFIG_FILE):
        if os.path.exists(CONFIG_EXAMPLE_FILE):
            try:
                import shutil
                shutil.copyfile(CONFIG_EXAMPLE_FILE, CONFIG_FILE)
            except Exception:
                pass
        else:
            return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading config.json: {e}")
        return {}

def verify_license(config_data):
    expire_str = config_data.get("license_expire_date", "2099-12-31")
    try:
        expire_date = datetime.datetime.strptime(expire_str, "%Y-%m-%d").date()
        today = datetime.date.today()
        if today > expire_date:
            return False, f"Lisensi Crypto Bot telah kedaluwarsa pada {expire_str}. Silakan hubungi penjual."
    except Exception:
        pass
    return True, "Lisensi Valid"

def load_latest_ai_results():
    if not os.path.exists(AI_RESULTS_FILE):
        return {}
    try:
        with open(AI_RESULTS_FILE, "r") as f:
            data = json.load(f)
            if "recommendation" in data:
                sym = data.get("symbol", "BTCUSDT")
                return {sym: data}
            return data
    except Exception:
        return {}

def save_latest_ai_results(data, symbol="BTCUSDT"):
    try:
        all_results = load_latest_ai_results()
        data["symbol"] = symbol
        all_results[symbol] = data
        with open(AI_RESULTS_FILE, "w") as f:
            json.dump(all_results, f, indent=2, default=json_serialize_helper)
    except Exception as e:
        logging.error(f"Error saving latest AI results: {e}")

def get_groq_crypto_analysis(symbol, timeframe_str, groq_api_key, config_data):
    ticker = exchange_api.get_ticker_price(symbol)
    df = exchange_api.get_crypto_klines(symbol, timeframe_str, limit=60)
    if df is None or len(df) < 20:
        return {"status": "error", "message": f"Data historis Crypto {symbol} tidak cukup."}

    df = strategy.calculate_crypto_indicators(df)
    curr_row = df.iloc[-1]
    
    prompt = f"""
    Anda adalah analis kuantitatif trading Crypto profesional.
    Tolong analisis pasangan koin {symbol} pada timeframe {timeframe_str}:
    - Harga Terkini: {ticker.get('last_price', curr_row['close'])}
    - EMA Fast (9): {curr_row['ema_fast']:.2f}
    - EMA Slow (21): {curr_row['ema_slow']:.2f}
    - RSI (14): {curr_row['rsi']:.2f}
    - MACD Line: {curr_row['macd_line']:.4f}, Signal: {curr_row['signal_line']:.4f}
    
    Berikan analisis presisi tinggi, tentukan Support & Resistance, lalu berikan rekomendasi (BUY, SELL, atau HOLD) beserta skor kepercayaan (0-100%).
    
    HARUS membalas HANYA dalam format JSON berikut:
    {{
      "recommendation": "BUY" atau "SELL" atau "HOLD",
      "confidence": nilai integer 0-100,
      "support": nilai float support,
      "resistance": nilai float resistance,
      "analysis": "Laporan analisis Crypto dalam Bahasa Indonesia. Gunakan tag HTML <h3>, <p>, <ul>, <li>."
    }}
    """

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "groq/compound-mini",
        "messages": [
            {"role": "system", "content": "You are a professional crypto trading analyst assistant. Respond ONLY in valid json format."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        if response.status_code != 200:
            if response.status_code == 429:
                time.sleep(1.5)
            payload["model"] = "openai/gpt-oss-20b"
            response = requests.post(url, headers=headers, json=payload, timeout=20)
            if response.status_code != 200:
                return {"status": "error", "message": f"Groq API HTTP {response.status_code}"}
                
        response_data = response.json()
        ai_text = response_data['choices'][0]['message']['content']
        if "```" in ai_text:
            parts = ai_text.split("```")
            for part in parts:
                part_str = part.strip()
                if part_str.startswith("json"):
                    part_str = part_str[4:].strip()
                if part_str.startswith("{"):
                    ai_text = part_str
                    break
        ai_json = json.loads(ai_text)
        
        return {
            "status": "success",
            "recommendation": ai_json.get("recommendation", "HOLD").upper(),
            "confidence": int(ai_json.get("confidence", 50)),
            "support": float(ai_json.get("support", ticker.get('last_price', 0.0))),
            "resistance": float(ai_json.get("resistance", ticker.get('last_price', 0.0))),
            "analysis": ai_json.get("analysis", "Analisis Crypto selesai.")
        }
    except Exception as e:
        return {"status": "error", "message": f"Groq Exception: {e}"}

def run_ai_crypto_analysis(symbol, timeframe_str, config_data):
    groq_api_key = config_data.get("groq_api_key", "").strip()
    if groq_api_key:
        logging.info(f"Running Groq AI Crypto Analysis for {symbol}...")
        res = get_groq_crypto_analysis(symbol, timeframe_str, groq_api_key, config_data)
        if res.get("status") == "success":
            return res
    return {"status": "error", "message": "Mohon masukkan API Key yang valid."}

_last_gainzalgo_scan = {}

def run_gainzalgo_v2_scan(symbol="BTCUSDT", timeframe_str="5m"):
    global _last_gainzalgo_scan
    cache_key = f"{symbol}_{timeframe_str}"
    
    df = exchange_api.get_crypto_klines(symbol, timeframe_str, limit=60)
    if df is None or len(df) < 20:
        if cache_key in _last_gainzalgo_scan:
            return _last_gainzalgo_scan[cache_key]
        return {"status": "error", "message": f"Data historis Crypto {symbol} tidak cukup."}

    gainz_data = strategy.calculate_gainzalgo_v2_signals(df)
    gainz_data["symbol"] = symbol
    gainz_data["timeframe"] = timeframe_str
    res = {"status": "success", "data": gainz_data}
    _last_gainzalgo_scan[cache_key] = res
    return res

last_trade_bar = {}
cycle_counter = 0

def bot_trading_cycle():
    global bot_running, last_trade_bar, cycle_counter
    cycle_counter += 1

    # 1. Update floating PnL and TP/SL status for open positions
    open_positions = exchange_api.update_paper_positions()

    config_data = load_config()
    symbols = config_data.get("symbols", ["BTCUSDT"])
    timeframe_str = config_data.get("timeframe", "5m")
    max_open_positions = int(config_data.get("max_open_positions", 2))
    min_confidence = int(config_data.get("min_confidence", 70))
    trade_amount = float(config_data.get("trade_lot_size", 0.01))

    current_open = len(exchange_api.paper_portfolio["positions"])
    
    # Active heartbeat / status logging
    if current_open >= max_open_positions:
        pos_str = " | ".join([f"{p['symbol']} #{p['ticket']}: ${p.get('price_current', p['price_open'])} (PnL: ${p.get('profit', 0):+.2f})" for p in exchange_api.paper_portfolio["positions"]])
        logging.info(f"[CYCLE #{cycle_counter}] Max posisi ({current_open}/{max_open_positions}) aktif. Memantau TP/SL real-time: {pos_str}")
        return

    logging.info(f"[CYCLE #{cycle_counter}] Memindai GainzAlgo V2 untuk {len(symbols)} koin ({', '.join(symbols)}) [{current_open}/{max_open_positions} slot aktif]...")

    for symbol in symbols:
        if not bot_running:
            break
        
        # Guard 1: Do not open duplicate position on the same symbol
        if exchange_api.has_open_position(symbol):
            continue

        if current_open >= max_open_positions:
            break

        df = exchange_api.get_crypto_klines(symbol, timeframe_str, limit=60)
        if df is not None and len(df) >= 20:
            gainz_data = strategy.calculate_gainzalgo_v2_signals(df)
            sig = gainz_data.get("signal")
            is_fresh = gainz_data.get("is_fresh_signal", False)
            conf = gainz_data.get("confidence", 50)
            entry = gainz_data.get("entry_price")
            tp = gainz_data.get("tp_price")
            sl = gainz_data.get("sl_price")

            latest_candle_time = int(df.iloc[-1].get("time", 0))

            # Guard 2: Only enter on a FRESH signal or strong high-confidence breakout
            # and ensure only 1 trade per candle bar timeframe
            if sig in ["BUY", "SELL"] and (is_fresh or conf >= min_confidence):
                if last_trade_bar.get(symbol) != latest_candle_time:
                    trading_mode = config_data.get("trading_mode", "paper")
                    logging.info(f"[SIGNAL TRIGGER] {symbol} {sig} on {timeframe_str} (Conf: {conf}%, Entry: {entry}, TP: {tp}, SL: {sl}) [Mode: {trading_mode}]")
                    
                    if trading_mode == "live_indodax":
                        indodax_key = config_data.get("indodax_api_key")
                        indodax_sec = config_data.get("indodax_secret_key")
                        if indodax_key and indodax_sec:
                            order_res = exchange_api.execute_indodax_order(
                                symbol=symbol,
                                side=sig,
                                price=entry,
                                quantity=trade_amount,
                                order_type="LIMIT",
                                api_key=indodax_key,
                                secret_key=indodax_sec
                            )
                            if order_res.get("status") == "success":
                                logging.info(f"[INDODAX REAL] Order {sig} #{order_res.get('data', {}).get('orderId')} sukses dikirim ke Indodax.")
                            else:
                                logging.error(f"[INDODAX REAL ERROR] Gagal mengirim order {sig} ke Indodax: {order_res.get('data') or order_res.get('message')}")
                        else:
                            logging.warning("[INDODAX] Mode Live dipilih namun API Key belum diisi. Order dilewati.")
                    else:
                        exchange_api.execute_paper_order(symbol, sig, trade_amount, entry, sl, tp)

                    last_trade_bar[symbol] = latest_candle_time
                    current_open += 1

