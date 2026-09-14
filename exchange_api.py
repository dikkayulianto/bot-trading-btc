import urllib.request
import ssl
import json
import logging
import time
import socket
import hmac
import hashlib
import requests
import pandas as pd
import numpy as np

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
    
    # Format KuCoin Symbol
    if not symbol_upper.endswith("-USDT") and symbol_upper.endswith("USDT"):
        coin = symbol_upper.replace("USDT", "")
        kucoin_symbol = f"{coin}-USDT"
    else:
        kucoin_symbol = symbol_upper

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
    sym_clean = symbol.upper().replace("/", "").replace("-", "")
    for p in paper_portfolio["positions"]:
        p_sym = p.get("symbol", "").upper().replace("/", "").replace("-", "")
        if p_sym == sym_clean:
            return True
    return False

def update_paper_positions():
    """
    Updates current price and floating PnL for open paper positions.
    Automatically closes positions when Take Profit or Stop Loss is reached.
    """
    if not paper_portfolio["positions"]:
        return []

    remaining = []
    for pos in paper_portfolio["positions"]:
        sym = pos.get("symbol", "")
        ticker = get_ticker_price(sym)
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
                paper_portfolio["balance_usdt"] += profit
                logging.info(f"[PAPER TRADING] #{pos['ticket']} {sym} HIT TAKE PROFIT (+${profit:.2f}) at {curr_price}")
                continue
            elif sl > 0 and curr_price <= sl:
                pos["profit"] = round(profit, 2)
                paper_portfolio["balance_usdt"] += profit
                logging.info(f"[PAPER TRADING] #{pos['ticket']} {sym} HIT STOP LOSS (-${abs(profit):.2f}) at {curr_price}")
                continue
        else: # SELL
            profit = (entry - curr_price) * amount
            if tp > 0 and curr_price <= tp:
                pos["profit"] = round(profit, 2)
                paper_portfolio["balance_usdt"] += profit
                logging.info(f"[PAPER TRADING] #{pos['ticket']} {sym} HIT TAKE PROFIT (+${profit:.2f}) at {curr_price}")
                continue
            elif sl > 0 and curr_price >= sl:
                pos["profit"] = round(profit, 2)
                paper_portfolio["balance_usdt"] += profit
                logging.info(f"[PAPER TRADING] #{pos['ticket']} {sym} HIT STOP LOSS (-${abs(profit):.2f}) at {curr_price}")
                continue

        pos["profit"] = round(profit, 2)
        remaining.append(pos)

    paper_portfolio["positions"] = remaining
    return paper_portfolio["positions"]

def get_paper_account_status():
    """
    Returns paper trading balance and positions after updating live prices.
    """
    update_paper_positions()
    total_profit = sum(p.get("profit", 0.0) for p in paper_portfolio["positions"])
    return {
        "balance": paper_portfolio["balance_usdt"],
        "balance_idr": paper_portfolio["balance_idr"],
        "equity": paper_portfolio["balance_usdt"] + total_profit,
        "floating_profit": total_profit,
        "mode": "Paper Trading (Simulasi)",
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
    logging.info(f"[PAPER TRADING] Executed {side.upper()} on {symbol} at {entry_price} (TP: {tp_price}, SL: {sl_price})")
    return pos

def close_paper_position(ticket):
    global paper_portfolio
    for i, pos in enumerate(paper_portfolio["positions"]):
        if int(pos.get("ticket", 0)) == int(ticket):
            profit = float(pos.get("profit", 0.0))
            paper_portfolio["balance_usdt"] += profit
            logging.info(f"[PAPER TRADING] Manual Close #{ticket} {pos.get('symbol')} (PnL: ${profit:.2f})")
            del paper_portfolio["positions"][i]
            return True
    return False

def close_all_paper_positions():
    global paper_portfolio
    total_closed = len(paper_portfolio["positions"])
    for pos in paper_portfolio["positions"]:
        profit = float(pos.get("profit", 0.0))
        paper_portfolio["balance_usdt"] += profit
    paper_portfolio["positions"] = []
    logging.info(f"[PAPER TRADING] Closed all {total_closed} paper positions.")
    return total_closed

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

    # Format pair to Indodax format (e.g. BTCUSDT -> btcidr or btcusdt)
    sym = symbol.lower().replace("/", "").replace("-", "")
    if sym.endswith("usdt"):
        pair_sym = sym
    elif sym.endswith("idr"):
        pair_sym = sym
    else:
        pair_sym = f"{sym}idr"

    ts = int(time.time() * 1000)
    params = {
        "symbol": pair_sym,
        "side": side.upper(),
        "type": order_type.upper(),
        "timestamp": ts,
        "recvWindow": 10000
    }
    if order_type.upper() == "LIMIT":
        params["price"] = str(price)
        params["quantity"] = str(quantity)
    elif order_type.upper() == "MARKET":
        if side.upper() == "BUY":
            params["quoteOrderQty"] = str(int(price * quantity))
        else:
            params["quantity"] = str(quantity)

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

