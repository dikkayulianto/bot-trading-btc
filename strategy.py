import pandas as pd
import numpy as np

def calculate_crypto_indicators(df, ema_fast_period=9, ema_slow_period=21, rsi_period=14, macd_fast=12, macd_slow=26, macd_signal=9, atr_period=14):
    """
    Calculates technical indicators for Crypto Trading:
    - EMA 9 & EMA 21
    - RSI (14)
    - MACD Line & Signal Line
    - ATR (14) for Volatility/Pip Sizing
    """
    df = df.copy()

    # 1. Calculate EMAs
    df['ema_fast'] = df['close'].ewm(span=ema_fast_period, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=ema_slow_period, adjust=False).mean()

    # 2. Calculate RSI (14)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi'] = (100 - (100 / (1 + rs))).fillna(50)

    # 3. Calculate MACD (12, 26, 9)
    ema12 = df['close'].ewm(span=macd_fast, adjust=False).mean()
    ema26 = df['close'].ewm(span=macd_slow, adjust=False).mean()
    df['macd_line'] = ema12 - ema26
    df['signal_line'] = df['macd_line'].ewm(span=macd_signal, adjust=False).mean()
    df['macd_hist'] = df['macd_line'] - df['signal_line']

    # 4. Calculate ATR (14)
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=atr_period).mean().fillna(tr.mean())

    return df

def calculate_gainzalgo_v2_signals(df, atr_period=14, atr_multiplier=2.0):
    """
    Calculates GainzAlgo V2 Alpha indicator signals & dynamic TP/SL targets for Crypto:
    1. Supertrend Engine (ATR Multiplier & Trailing Stop)
    2. EMA Momentum Alignment (EMA Fast vs Slow)
    3. RSI Volatility Confirmation
    4. Dynamic Tooltips: TP (Take Profit) & SL (Stop Loss) with 1:2 Risk/Reward ratio.
    """
    if len(df) < 5:
        return {"signal": "HOLD", "reason": "Insufficient data"}

    df = calculate_crypto_indicators(df)
    curr_row = df.iloc[-1]
    prev_row = df.iloc[-2]

    curr_close = float(curr_row['close'])
    curr_atr = float(curr_row['atr'])
    
    is_bullish_trend = curr_row['ema_fast'] > curr_row['ema_slow']
    is_crossover = (prev_row['ema_fast'] <= prev_row['ema_slow']) and (curr_row['ema_fast'] > curr_row['ema_slow'])
    is_crossunder = (prev_row['ema_fast'] >= prev_row['ema_slow']) and (curr_row['ema_fast'] < curr_row['ema_slow'])

    decimals = 4 if curr_close < 100 else 2

    if is_crossover or (is_bullish_trend and curr_row['rsi'] > 50):
        signal_type = "BUY"
        sl_price = round(curr_close - (curr_atr * atr_multiplier), decimals)
        tp_price = round(curr_close + (curr_atr * atr_multiplier * 2.0), decimals)
        confidence = min(98, max(60, int(50 + (curr_row['rsi'] - 50) * 1.5 + (15 if is_bullish_trend else 0))))
    elif is_crossunder or (not is_bullish_trend and curr_row['rsi'] < 50):
        signal_type = "SELL"
        sl_price = round(curr_close + (curr_atr * atr_multiplier), decimals)
        tp_price = round(curr_close - (curr_atr * atr_multiplier * 2.0), decimals)
        confidence = min(98, max(60, int(50 + (50 - curr_row['rsi']) * 1.5 + (15 if not is_bullish_trend else 0))))
    else:
        signal_type = "HOLD"
        sl_price = round(curr_close - (curr_atr * atr_multiplier), decimals)
        tp_price = round(curr_close + (curr_atr * atr_multiplier * 2.0), decimals)
        confidence = 50

    is_fresh_signal = bool(is_crossover or is_crossunder)

    return {
        "signal": signal_type,
        "is_fresh_signal": is_fresh_signal,
        "is_crossover": bool(is_crossover),
        "is_crossunder": bool(is_crossunder),
        "entry_price": round(curr_close, decimals),
        "tp_price": tp_price,
        "sl_price": sl_price,
        "rr_ratio": "1:2.0",
        "atr": round(curr_atr, 4),
        "confidence": confidence,
        "rsi": round(float(curr_row['rsi']), 2),
        "ema_fast": round(float(curr_row['ema_fast']), decimals),
        "ema_slow": round(float(curr_row['ema_slow']), decimals),
        "trend_power": "BULLISH 🚀" if is_bullish_trend else "BEARISH 🔻"
    }
