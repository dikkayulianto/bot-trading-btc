import os
import math
import urllib.request
import ssl
import json
import logging
import time
import socket
import hmac
import hashlib
import requests
import datetime
import pandas as pd
import numpy as np

# Persistence files
POSITIONS_FILE = os.path.join(os.path.dirname(__file__), "active_positions.json")
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "trade_history.json")

def _load_app_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def record_paper_history(pos, close_price, profit, reason="MANUAL CLOSE"):
    try:
        history = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    history = data
        now = time.time()
        record = {
            "order_id": str(pos.get("ticket", "")),
            "symbol": pos.get("symbol", ""),
            "side": pos.get("type", "BUY"),
            "amount": float(pos.get("amount", 0)),
            "price_open": float(pos.get("price_open", close_price)),
            "price_close": float(close_price),
            "profit": round(float(profit), 2),
            "profit_idr": round(float(profit), 2) if pos.get("currency") == "IDR" else 0,
            "currency": pos.get("currency", "USDT"),
            "mode": pos.get("mode", "paper"),
            "reason": reason,
            "time": int(now * 1000),
            "datetime": datetime.datetime.fromtimestamp(now).strftime("%d/%m/%Y %H:%M:%S")
        }
        history.insert(0, record)
        history = history[:200]
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving paper trade history: {e}")


def save_positions_to_disk():
    try:
        with open(POSITIONS_FILE, "w") as f:
            json.dump(paper_portfolio.get("positions", []), f, indent=2)
    except Exception as e:
        logging.error(f"Error saving active positions to disk: {e}")

def load_saved_positions():
    if os.path.exists(POSITIONS_FILE):
        try:
            with open(POSITIONS_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    paper_portfolio["positions"] = data
                    logging.info(f"Loaded {len(data)} active position(s) from {POSITIONS_FILE}")
        except Exception as e:
            logging.error(f"Error loading active positions from disk: {e}")


# Ensure IPv4 resolution for api.indodax.com to match whitelisted IPv4 address
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_indodax_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == "api.indodax.com":
        return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    return _orig_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = _ipv4_indodax_getaddrinfo

# Configure SSL context bypass for Windows Python HTTPS requests
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# In-Memory Paper Trading Portfolio
paper_portfolio = {
    "balance_usdt": 10000.0,
    "balance_idr": 150000000.0,
    "positions": []
}

# Load persisted positions from active_positions.json if available
load_saved_positions()


# Real-time data caching (TTL in seconds)
_ticker_cache = {}
_kline_cache = {}
_indodax_account_cache = {}
TICKER_CACHE_TTL = 3.0
KLINE_CACHE_TTL = 6.0

def get_ticker_price(symbol="BTCUSDT"):
    """
    Fetches real-time price for a crypto symbol from KuCoin / Indodax / Bybit.
    """
    symbol_upper = symbol.upper().replace("/", "").replace("-", "")
    
    # Check cache first
    now = time.time()
    cached = _ticker_cache.get(symbol_upper)
    if cached and (now - cached["timestamp"] < TICKER_CACHE_TTL):
        return cached["data"]

    # 1. Check Indodax for IDR pairs
    if "IDR" in symbol_upper or symbol_upper.endswith("IDR"):
        coin = symbol_upper.replace("IDR", "").lower()
        url = f"https://indodax.com/api/ticker/{coin}idr"
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            res = urllib.request.urlopen(req, context=ssl_ctx, timeout=10).read().decode('utf-8')
            data = json.loads(res)
            ticker = data.get("ticker", {})
            last_price = float(ticker.get("last", 0.0))
            result = {
                "symbol": f"{coin.upper()}/IDR",
                "last_price": last_price,
                "high": float(ticker.get("high", last_price)),
                "low": float(ticker.get("low", last_price)),
                "volume": float(ticker.get("vol_" + coin, 0.0)),
                "exchange": "Indodax"
            }
            _ticker_cache[symbol_upper] = {"data": result, "timestamp": now}
            return result
        except Exception as e:
            logging.error(f"Error fetching Indodax price for {symbol}: {e}")

    # 2. Check KuCoin for USDT pairs
    kucoin_symbol = symbol_upper
    if not kucoin_symbol.endswith("-USDT") and kucoin_symbol.endswith("USDT"):
        coin = kucoin_symbol.replace("USDT", "")
        kucoin_symbol = f"{coin}-USDT"

    url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={kucoin_symbol}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        res = urllib.request.urlopen(req, context=ssl_ctx, timeout=10).read().decode('utf-8')
        data = json.loads(res)
        if data.get("code") == "200000" and data.get("data"):
            last_price = float(data["data"].get("price", 0.0))
            result = {
                "symbol": symbol_upper,
                "last_price": last_price,
                "high": float(data["data"].get("bestAsk", last_price)),
                "low": float(data["data"].get("bestBid", last_price)),
                "volume": float(data["data"].get("size", 0.0)),
                "exchange": "KuCoin"
            }
            _ticker_cache[symbol_upper] = {"data": result, "timestamp": now}
            return result
    except Exception as e:
        logging.error(f"Error fetching KuCoin price for {symbol}: {e}")

    # Fallback default
    fallback = {"symbol": symbol_upper, "last_price": 0.0, "exchange": "Unknown"}
    return fallback

def get_crypto_klines(symbol="BTCUSDT", timeframe="5m", limit=100):
    """
    Fetches historical OHLCV candlestick data for technical analysis.
    """
    symbol_upper = symbol.upper().replace("/", "").replace("-", "")
    cache_key = (symbol_upper, timeframe.lower(), limit)
    now = time.time()
    
    cached = _kline_cache.get(cache_key)
    if cached and (now - cached["timestamp"] < KLINE_CACHE_TTL):
        return cached["df"].copy()
    
    # Format KuCoin Symbol for reliable candle fetching
    coin = symbol_upper.replace("USDT", "").replace("IDR", "").replace("-", "").replace("/", "")
    kucoin_symbol = f"{coin}-USDT"

    tf_map = {"1m": "1min", "5m": "5min", "15m": "15min", "1h": "1hour", "4h": "4hour", "1d": "1day"}
    kc_tf = tf_map.get(timeframe.lower(), "5min")

    url = f"https://api.kucoin.com/api/v1/market/candles?symbol={kucoin_symbol}&type={kc_tf}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        res = urllib.request.urlopen(req, context=ssl_ctx, timeout=10).read().decode('utf-8')
        data = json.loads(res)
        if data.get("code") == "200000" and data.get("data"):
            raw_candles = data["data"][:limit]
            # KuCoin candles: [time, open, close, high, low, volume, turnover]
            parsed = []
            for c in reversed(raw_candles):
                parsed.append({
                    "time": int(c[0]),
                    "open": float(c[1]),
                    "close": float(c[2]),
                    "high": float(c[3]),
                    "low": float(c[4]),
                    "volume": float(c[5])
                })
            df = pd.DataFrame(parsed)
            _kline_cache[cache_key] = {"df": df, "timestamp": now}
            return df
    except Exception as e:
        logging.error(f"Error fetching crypto klines for {symbol}: {e}")

    # Return empty DataFrame fallback
    return pd.DataFrame(columns=["time", "open", "close", "high", "low", "volume"])

def has_open_position(symbol):
    """
    Checks if there is already an active position for this symbol.
    """
    sym_clean = symbol.upper().replace("/", "").replace("-", "").replace("USDT", "").replace("IDR", "")
    for p in paper_portfolio.get("positions", []):
        p_sym = p.get("symbol", "").upper().replace("/", "").replace("-", "").replace("USDT", "").replace("IDR", "")
        if p_sym == sym_clean:
            return True
    return False

def add_live_position(symbol, side, amount, entry_price, sl_price, tp_price, ticket_id=None, mode="live_indodax", currency="IDR"):
    """
    Records an active live trading position (e.g. Indodax) for real-time tracking, TP/SL, and dashboard display.
    """
    if not ticket_id:
        ticket_id = f"live-{int(time.time())}"
    
    pos = {
        "ticket": str(ticket_id),
        "symbol": symbol.upper().replace("/", "").replace("-", ""),
        "type": side.upper(),
        "mode": mode,
        "currency": currency,
        "amount": round(float(amount), 6),
        "price_open": float(entry_price),
        "price_current": float(entry_price),
        "sl": float(sl_price) if sl_price else 0.0,
        "tp": float(tp_price) if tp_price else 0.0,
        "profit": 0.0,
        "profit_idr": 0.0
    }
    paper_portfolio["positions"].append(pos)
    save_positions_to_disk()
    logging.info(f"[LIVE POSITION] #{ticket_id} {side.upper()} {symbol} dicatat ke portfolio aktif (Qty: {amount}, Entry: {entry_price}, TP: {tp_price}, SL: {sl_price})")
    return pos

def get_safe_sell_quantity(coin, desired_qty, api_key, secret_key):
    """
    Computes a safe sell quantity floored to asset precision to avoid 'Insufficient balance'.
    """
    acc = get_indodax_account_info(api_key, secret_key)
    coin_free = 0.0
    for b in acc.get("balances", []):
        if b.get("asset") == coin.upper():
            coin_free = float(b.get("free", 0.0))
            break
    
    qty = min(desired_qty, coin_free) if desired_qty > 0 else coin_free
    if qty <= 0:
        return 0.0
    
    coin_u = coin.upper()
    if coin_u in ["BTC", "ETH", "SOL"]:
        factor = 1000000 # 6 decimals
    elif coin_u in ["XRP", "SUI", "ADA", "ONDO"]:
        factor = 10000 # 4 decimals
    else:
        factor = 100 # 2 decimals (e.g. DOGE)
    
    return math.floor(qty * factor) / factor

def sync_indodax_wallet_positions():
    """
    Synchronizes open positions with the real Indodax wallet holdings.
    Ensures any coin held in Indodax (like SOL, DOGE, XRP) is tracked with live PnL.
    """
    cfg = _load_app_config()
    key = cfg.get("indodax_api_key")
    sec = cfg.get("indodax_secret_key")
    if not key or not sec or cfg.get("trading_mode") != "live_indodax":
        return paper_portfolio["positions"]

    acc = get_indodax_account_info(key, sec)
    if acc.get("status") != "success":
        return paper_portfolio["positions"]

    ts = int(time.time() * 1000)
    synced_positions = []
    existing_map = {p.get("symbol", "").upper().replace("USDT","").replace("IDR",""): p for p in paper_portfolio.get("positions", [])}

    for b in acc.get("balances", []):
        asset = b.get("asset", "").upper()
        free = float(b.get("free", 0.0))
        if asset in ["IDR", "USDT"] or free <= 0:
            continue

        pair = f"{asset.lower()}idr"
        ticker = get_ticker_price(f"{asset}IDR")
        curr_price = float(ticker.get("last_price", 0.0))
        est_val = free * curr_price
        if est_val < 10000:  # Skip dust less than Rp 10.000
            continue

        if asset in existing_map:
            pos = existing_map[asset]
            pos["amount"] = round(free, 6)
            pos["price_current"] = curr_price
            entry = float(pos.get("price_open", curr_price))
            pos["profit"] = round((curr_price - entry) * free, 0)
            pos["profit_idr"] = pos["profit"]
            synced_positions.append(pos)
        else:
            entry_price = curr_price
            ticket_id = f"{asset.lower()}-{int(time.time())}"
            try:
                q = f"symbol={pair}&timestamp={ts}&recvWindow=10000"
                sig = hmac.new(sec.encode("utf-8"), q.encode("utf-8"), hashlib.sha256).hexdigest()
                headers = {"Accept": "application/json", "X-APIKEY": key, "Sign": sig}
                r = requests.get(f"https://api.indodax.com/api/v2/myTrades?{q}", headers=headers, timeout=5)
                if r.status_code == 200:
                    trades = r.json().get("data", [])
                    buy_trades = [t for t in trades if t.get("isBuyer")]
                    if buy_trades:
                        latest_buy = buy_trades[0]
                        entry_price = float(latest_buy.get("price", curr_price))
                        raw_order_id = str(latest_buy.get("orderId", ticket_id))
                        ticket_id = raw_order_id.replace(f"{pair}-market-", "")
            except Exception as e:
                logging.error(f"Error querying trades for {asset}: {e}")

            sl_pct = float(cfg.get("sl_percent", 1.5)) / 100.0
            tp_pct = float(cfg.get("tp_percent", 3.0)) / 100.0
            sl = round(entry_price * (1.0 - sl_pct), 0 if entry_price > 10 else 2)
            tp = round(entry_price * (1.0 + tp_pct), 0 if entry_price > 10 else 2)
            profit = round((curr_price - entry_price) * free, 0)

            new_pos = {
                "ticket": str(ticket_id),
                "symbol": f"{asset}IDR",
                "type": "BUY",
                "mode": "live_indodax",
                "currency": "IDR",
                "amount": round(free, 6),
                "price_open": entry_price,
                "price_current": curr_price,
                "sl": sl,
                "tp": tp,
                "profit": profit,
                "profit_idr": profit
            }
            synced_positions.append(new_pos)
            logging.info(f"[INDODAX WALLET SYNC] Menemukan aset {asset} di dompet: {free} @ Rp {entry_price:,.0f} (#{ticket_id})")

    paper_portfolio["positions"] = synced_positions
    save_positions_to_disk()
    return paper_portfolio["positions"]

def update_paper_positions():
    """
    Updates current price and floating PnL for open positions (paper & live Indodax).
    Automatically closes positions when Take Profit or Stop Loss is reached.
    """
    cfg = _load_app_config()
    is_live_mode = cfg.get("trading_mode") == "live_indodax"

    if is_live_mode:
        sync_indodax_wallet_positions()

    if not paper_portfolio["positions"]:
        return []

    remaining = []
    for pos in paper_portfolio["positions"]:
        sym = pos.get("symbol", "")
        is_live = pos.get("mode") == "live_indodax" or pos.get("currency") == "IDR"

        query_sym = sym
        if is_live and not query_sym.endswith("IDR"):
            query_sym = query_sym.replace("USDT", "") + "IDR"

        ticker = get_ticker_price(query_sym)
        curr_price = float(ticker.get("last_price", 0.0))
        if curr_price <= 0:
            remaining.append(pos)
            continue

        pos["price_current"] = curr_price
        side = pos.get("type", "BUY")
        entry = float(pos.get("price_open", curr_price))
        amount = float(pos.get("amount", 0.01))
        sl = float(pos.get("sl", 0.0))
        tp = float(pos.get("tp", 0.0))

        if side == "BUY":
            profit = (curr_price - entry) * amount
            if tp > 0 and curr_price >= tp:
                pos["profit"] = round(profit, 2)
                if is_live:
                    logging.info(f"[INDODAX AUTO TP] #{pos['ticket']} {sym} HIT TAKE PROFIT (+Rp {profit:,.0f}) di harga {curr_price}! Mengirim MARKET SELL...")
                    indodax_k = cfg.get("indodax_api_key")
                    indodax_s = cfg.get("indodax_secret_key")
                    if indodax_k and indodax_s:
                        coin = sym.replace("IDR", "").replace("USDT", "")
                        safe_qty = get_safe_sell_quantity(coin, amount, indodax_k, indodax_s)
                        if safe_qty > 0:
                            execute_indodax_order(sym, "SELL", curr_price, safe_qty, order_type="MARKET", api_key=indodax_k, secret_key=indodax_s)
                else:
                    paper_portfolio["balance_usdt"] += profit
                    record_paper_history(pos, curr_price, profit, reason="TAKE PROFIT")
                    logging.info(f"[PAPER TRADING] #{pos['ticket']} {sym} HIT TAKE PROFIT (+${profit:.2f}) at {curr_price}")
                continue
            elif sl > 0 and curr_price <= sl:
                pos["profit"] = round(profit, 2)
                if is_live:
                    logging.info(f"[INDODAX AUTO SL] #{pos['ticket']} {sym} HIT STOP LOSS (-Rp {abs(profit):,.0f}) di harga {curr_price}! Mengirim MARKET SELL...")
                    indodax_k = cfg.get("indodax_api_key")
                    indodax_s = cfg.get("indodax_secret_key")
                    if indodax_k and indodax_s:
                        coin = sym.replace("IDR", "").replace("USDT", "")
                        safe_qty = get_safe_sell_quantity(coin, amount, indodax_k, indodax_s)
                        if safe_qty > 0:
                            execute_indodax_order(sym, "SELL", curr_price, safe_qty, order_type="MARKET", api_key=indodax_k, secret_key=indodax_s)
                else:
                    paper_portfolio["balance_usdt"] += profit
                    record_paper_history(pos, curr_price, profit, reason="STOP LOSS")
                    logging.info(f"[PAPER TRADING] #{pos['ticket']} {sym} HIT STOP LOSS (-${abs(profit):.2f}) at {curr_price}")
                continue
        else: # SELL
            profit = (entry - curr_price) * amount
            if tp > 0 and curr_price <= tp:
                pos["profit"] = round(profit, 2)
                paper_portfolio["balance_usdt"] += profit
                record_paper_history(pos, curr_price, profit, reason="TAKE PROFIT")
                logging.info(f"[PAPER TRADING] #{pos['ticket']} {sym} HIT TAKE PROFIT (+${profit:.2f}) at {curr_price}")
                continue
            elif sl > 0 and curr_price >= sl:
                pos["profit"] = round(profit, 2)
                paper_portfolio["balance_usdt"] += profit
                record_paper_history(pos, curr_price, profit, reason="STOP LOSS")
                logging.info(f"[PAPER TRADING] #{pos['ticket']} {sym} HIT STOP LOSS (-${abs(profit):.2f}) at {curr_price}")
                continue

        pos["profit"] = round(profit, 2) if not is_live else round(profit, 0)
        if is_live:
            pos["profit_idr"] = pos["profit"]
        remaining.append(pos)

    paper_portfolio["positions"] = remaining
    save_positions_to_disk()
    return paper_portfolio["positions"]

def get_paper_account_status():
    """
    Returns paper trading balance and positions after updating live prices.
    """
    update_paper_positions()
    total_profit = sum(p.get("profit", 0.0) for p in paper_portfolio["positions"])
    cfg = _load_app_config()
    is_live_mode = cfg.get("trading_mode") == "live_indodax"
    return {
        "balance": paper_portfolio["balance_usdt"],
        "balance_idr": paper_portfolio["balance_idr"],
        "equity": paper_portfolio["balance_usdt"] + total_profit,
        "floating_profit": total_profit,
        "mode": "Live Indodax (Real)" if is_live_mode else "Paper Trading (Simulasi)",
        "exchange": "KuCoin / Indodax REST API",
        "positions": paper_portfolio["positions"]
    }

def execute_paper_order(symbol, side, amount, entry_price, sl_price, tp_price):
    """
    Executes a virtual Paper Trading order.
    """
    ticket_id = len(paper_portfolio["positions"]) + 10001
    pos = {
        "ticket": ticket_id,
        "symbol": symbol,
        "type": side.upper(),
        "amount": amount,
        "price_open": entry_price,
        "price_current": entry_price,
        "sl": sl_price,
        "tp": tp_price,
        "profit": 0.0
    }
    paper_portfolio["positions"].append(pos)
    save_positions_to_disk()
    logging.info(f"[PAPER TRADING] Executed {side.upper()} on {symbol} at {entry_price} (TP: {tp_price}, SL: {sl_price})")
    return pos

def close_paper_position(ticket):
    global paper_portfolio
    for i, pos in enumerate(paper_portfolio["positions"]):
        if str(pos.get("ticket", "")) == str(ticket):
            profit = float(pos.get("profit", 0.0))
            is_live = pos.get("mode") == "live_indodax"
            if is_live:
                cfg = _load_app_config()
                sym = pos.get("symbol", "")
                coin = sym.replace("IDR", "").replace("USDT", "")
                safe_qty = get_safe_sell_quantity(coin, float(pos.get("amount", 0.0)), cfg.get("indodax_api_key"), cfg.get("indodax_secret_key"))
                if safe_qty > 0:
                    logging.info(f"[INDODAX MANUAL CLOSE] Menjual #{ticket} {coin} (Qty: {safe_qty}) di pasar Indodax...")
                    execute_indodax_order(sym, "SELL", 0, safe_qty, order_type="MARKET", api_key=cfg.get("indodax_api_key"), secret_key=cfg.get("indodax_secret_key"))
            else:
                paper_portfolio["balance_usdt"] += profit
                record_paper_history(pos, pos.get("price_current", pos.get("price_open")), profit, reason="MANUAL CLOSE")
                logging.info(f"[PAPER TRADING] Manual Close #{ticket} {pos.get('symbol')} (PnL: ${profit:.2f})")
            del paper_portfolio["positions"][i]
            save_positions_to_disk()
            return True
    return False

def close_all_paper_positions():
    global paper_portfolio
    cfg = _load_app_config()
    total_closed = len(paper_portfolio["positions"])
    for pos in list(paper_portfolio["positions"]):
        if pos.get("mode") == "live_indodax":
            sym = pos.get("symbol", "")
            coin = sym.replace("IDR", "").replace("USDT", "")
            safe_qty = get_safe_sell_quantity(coin, float(pos.get("amount", 0.0)), cfg.get("indodax_api_key"), cfg.get("indodax_secret_key"))
            if safe_qty > 0:
                logging.info(f"[INDODAX CLOSE ALL] Menjual {coin} (Qty: {safe_qty}) di pasar Indodax...")
                execute_indodax_order(sym, "SELL", 0, safe_qty, order_type="MARKET", api_key=cfg.get("indodax_api_key"), secret_key=cfg.get("indodax_secret_key"))
        else:
            profit = float(pos.get("profit", 0.0))
            paper_portfolio["balance_usdt"] += profit
            record_paper_history(pos, pos.get("price_current", pos.get("price_open")), profit, reason="CLOSE ALL")
    paper_portfolio["positions"] = []
    save_positions_to_disk()
    logging.info(f"Closed all {total_closed} active positions.")
    return total_closed

# ============================================================
# TRADE HISTORY CONNECTOR & LOGIC
# ============================================================

_trade_history_cache = {"timestamp": 0, "data": None}
TRADE_HISTORY_CACHE_TTL = 4.0

def get_indodax_trade_history(limit=100):
    cfg = _load_app_config()
    key = cfg.get("indodax_api_key")
    sec = cfg.get("indodax_secret_key")
    if not key or not sec:
        return {"status": "error", "message": "Indodax API Key belum diatur.", "history": [], "summary": {}}

    now = time.time()
    if _trade_history_cache["timestamp"] and (now - _trade_history_cache["timestamp"] < TRADE_HISTORY_CACHE_TTL) and _trade_history_cache["data"]:
        return _trade_history_cache["data"]

    symbols_to_query = set()
    for s in cfg.get("symbols", []):
        coin = s.upper().replace("USDT", "").replace("IDR", "").replace("-", "").replace("/", "").lower()
        if coin:
            symbols_to_query.add(f"{coin}idr")
    for default_coin in ["xrpidr", "dogeidr", "solidr", "suiidr", "btcidr", "ethidr", "ondoidr"]:
        symbols_to_query.add(default_coin)

    ts = int(now * 1000)
    order_map = {}

    for sym in symbols_to_query:
        try:
            q = f"symbol={sym}&timestamp={ts}&recvWindow=10000"
            sig = hmac.new(sec.encode("utf-8"), q.encode("utf-8"), hashlib.sha256).hexdigest()
            headers = {"Accept": "application/json", "X-APIKEY": key, "Sign": sig}
            r = requests.get(f"https://api.indodax.com/api/v2/myTrades?{q}", headers=headers, timeout=5)
            if r.status_code == 200:
                for t in r.json().get("data", []):
                    oid = str(t.get("orderId"))
                    qty = float(t.get("qty", 0))
                    quote_qty = float(t.get("quoteQty", 0))
                    commission = float(t.get("commission", 0))
                    if oid not in order_map:
                        order_map[oid] = {
                            "order_id": oid.split("-")[-1],
                            "full_order_id": oid,
                            "symbol": t.get("symbol").upper(),
                            "side": "BUY" if t.get("isBuyer") else "SELL",
                            "time": t.get("time"),
                            "qty": qty,
                            "quote_qty": quote_qty,
                            "commission": commission,
                            "currency": "IDR",
                            "mode": "live_indodax"
                        }
                    else:
                        order_map[oid]["qty"] += qty
                        order_map[oid]["quote_qty"] += quote_qty
                        order_map[oid]["commission"] += commission
        except Exception as e:
            logging.error(f"Error fetching trade history for {sym}: {e}")

    trades = list(order_map.values())
    trades.sort(key=lambda x: x["time"])  # chronological order for matching

    last_buy_price = {}
    total_buy_vol = 0.0
    total_sell_vol = 0.0
    total_realized_profit = 0.0

    for t in trades:
        sym = t["symbol"]
        t["price"] = round(t["quote_qty"] / t["qty"], 2) if t["qty"] > 0 else 0
        t["datetime"] = datetime.datetime.fromtimestamp(t["time"] / 1000).strftime("%d/%m/%Y %H:%M:%S")
        if t["side"] == "BUY":
            last_buy_price[sym] = t["price"]
            t["pnl"] = 0.0
            total_buy_vol += t["quote_qty"]
        else:
            buy_p = last_buy_price.get(sym, t["price"])
            pnl = round((t["price"] - buy_p) * t["qty"] - t["commission"], 0)
            t["pnl"] = pnl
            total_realized_profit += pnl
            total_sell_vol += t["quote_qty"]

    trades.sort(key=lambda x: x["time"], reverse=True)  # newest first
    limited_trades = trades[:limit]

    summary = {
        "total_trades": len(trades),
        "total_buy_volume_idr": round(total_buy_vol, 0),
        "total_sell_volume_idr": round(total_sell_vol, 0),
        "total_realized_profit_idr": round(total_realized_profit, 0),
        "mode": "live_indodax"
    }

    result = {"status": "success", "history": limited_trades, "summary": summary}
    _trade_history_cache["timestamp"] = now
    _trade_history_cache["data"] = result
    return result

def get_trade_history(mode=None, limit=100):
    cfg = _load_app_config()
    current_mode = mode or cfg.get("trading_mode", "paper")
    if current_mode == "live_indodax":
        return get_indodax_trade_history(limit=limit)
    else:
        history = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        history = data
            except Exception:
                pass
        total_pnl = sum(h.get("profit", 0) for h in history)
        summary = {
            "total_trades": len(history),
            "total_realized_profit": round(total_pnl, 2),
            "mode": "paper"
        }
        return {"status": "success", "history": history[:limit], "summary": summary}



# ============================================================
# INDODAX TRADE API 2.0 CONNECTOR
# ============================================================

def get_indodax_account_info(api_key, secret_key):
    """
    Fetches real account info and balances from Indodax Trade API 2.0 (GET /api/v2/account).
    """
    if not api_key or not secret_key:
        return {"status": "unconfigured", "message": "Indodax API Key belum diatur."}

    now = time.time()
    if _indodax_account_cache.get("timestamp") and (now - _indodax_account_cache["timestamp"] < 4.0):
        return _indodax_account_cache["data"]

    try:
        ts = int(now * 1000)
        query = f"omitZeroBalances=true&recvWindow=10000&timestamp={ts}"
        sig = hmac.new(secret_key.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
        url = f"https://api.indodax.com/api/v2/account?{query}"
        headers = {
            "Accept": "application/json",
            "X-APIKEY": api_key,
            "Sign": sig,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            balances = data.get("balances", [])
            idr_balance = 0.0
            for b in balances:
                if b.get("asset") == "IDR":
                    idr_balance = float(b.get("free", 0.0))
                    break
            result = {
                "status": "success",
                "uid": data.get("uid"),
                "canTrade": data.get("canTrade", False),
                "canWithdraw": data.get("canWithdraw", False),
                "accountType": data.get("accountType", "individual"),
                "balances": balances,
                "idr_balance": idr_balance
            }
            _indodax_account_cache["data"] = result
            _indodax_account_cache["timestamp"] = now
            return result
        else:
            return {
                "status": "error",
                "code": resp.status_code,
                "message": resp.text
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def execute_indodax_order(symbol, side, price, quantity, order_type="LIMIT", api_key=None, secret_key=None):
    """
    Executes a real Spot Order on Indodax Trade API 2.0 (POST /api/v2/order).
    """
    if not api_key or not secret_key:
        return {"status": "error", "message": "Indodax API Key dan Secret Key diperlukan."}

    # Extract base coin e.g. BTC from BTCUSDT or BTCIDR
    coin = symbol.lower().replace("/", "").replace("-", "").replace("usdt", "").replace("idr", "")
    pair_sym = f"{coin}idr"

    ts = int(time.time() * 1000)
    params = {
        "symbol": pair_sym,
        "side": side.upper(),
        "type": order_type.upper(),
        "timestamp": ts,
        "recvWindow": 10000
    }
    if order_type.upper() == "LIMIT":
        # Get live Indodax IDR price if price was passed in USD
        if price < 1000000 and "btc" in pair_sym:
            ticker = get_ticker_price(f"{coin.upper()}IDR")
            actual_price = ticker.get("last_price", price * 15500)
        else:
            actual_price = price
        params["price"] = str(int(actual_price))
        params["quantity"] = str(quantity)
    elif order_type.upper() == "MARKET":
        if side.upper() == "BUY":
            # For BUY MARKET on Indodax, quoteOrderQty must be IDR amount (minimum Rp 10,000)
            idr_nominal = int(quantity) if quantity >= 10000 else 50000
            params["quoteOrderQty"] = str(idr_nominal)
        else:
            params["quantity"] = str(round(quantity, 6))

    body_str = urllib.parse.urlencode(params)
    sig = hmac.new(secret_key.encode("utf-8"), body_str.encode("utf-8"), hashlib.sha256).hexdigest()

    url = "https://api.indodax.com/api/v2/order"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-APIKEY": api_key,
        "Sign": sig,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    }

    try:
        resp = requests.post(url, data=body_str, headers=headers, timeout=10)
        res_data = resp.json()
        if resp.status_code == 200 and not res_data.get("code"):
            logging.info(f"[INDODAX LIVE ORDER] Sukses {side.upper()} {pair_sym}: {res_data}")
            return {"status": "success", "data": res_data}
        else:
            logging.error(f"[INDODAX LIVE ORDER ERROR] {pair_sym}: {res_data}")
            return {"status": "error", "data": res_data}
    except Exception as e:
        logging.error(f"[INDODAX ORDER EXCEPTION] {e}")
        return {"status": "error", "message": str(e)}

