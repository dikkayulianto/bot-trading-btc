import os
import json
import threading
import time
from flask import Flask, render_template, jsonify, request, send_from_directory

import bot
import exchange_api
import strategy

app = Flask(__name__)

bot_thread = None

def background_trading_loop():
    while True:
        if bot.bot_running:
            try:
                bot.bot_trading_cycle()
            except Exception as e:
                bot.logger.error(f"Error in crypto background trading loop: {e}")
        
        cfg = bot.load_config()
        interval = int(cfg.get("loop_interval_seconds", 15))
        time.sleep(max(5, interval))

def ensure_bot_thread():
    global bot_thread
    if bot_thread is None or not bot_thread.is_alive():
        bot_thread = threading.Thread(target=background_trading_loop, daemon=True)
        bot_thread.start()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)

@app.route("/api/status", methods=["GET"])
def api_status():
    config = bot.load_config()
    is_valid, msg = bot.verify_license(config)
    paper_status = exchange_api.get_paper_account_status()
    latest_ai_map = bot.load_latest_ai_results()
    
    current_symbol = request.args.get("symbol")
    if not current_symbol:
        current_symbol = config.get("symbols", ["BTCUSDT"])[0] if config.get("symbols") else "BTCUSDT"
    
    timeframe = request.args.get("timeframe") or config.get("timeframe", "5m")
    gainz_res = bot.run_gainzalgo_v2_scan(current_symbol, timeframe)
    
    # Strictly get latest AI for current symbol
    ai_for_symbol = latest_ai_map.get(current_symbol, {})

    # Indodax Real Account info if configured
    indodax_status = {}
    if config.get("indodax_api_key") and config.get("indodax_secret_key"):
        indodax_status = exchange_api.get_indodax_account_info(
            config.get("indodax_api_key"),
            config.get("indodax_secret_key")
        )

    return jsonify({
        "bot_running": bot.bot_running,
        "license_valid": is_valid,
        "license_message": msg,
        "account": paper_status,
        "indodax_account": indodax_status,
        "config": config,
        "selected_symbol": current_symbol,
        "logs": list(bot.log_history),
        "latest_ai": ai_for_symbol or {},
        "all_ai_results": latest_ai_map,
        "gainzalgo_v2": gainz_res.get("data") if gainz_res.get("status") == "success" else {}
    })

@app.route("/api/start", methods=["POST"])
def api_start():
    config = bot.load_config()
    is_valid, msg = bot.verify_license(config)
    if not is_valid:
        return jsonify({"status": "error", "message": msg}), 400
    
    bot.bot_running = True
    ensure_bot_thread()
    bot.logger.info("Bot Trading Crypto (Port 5007) DIJALANKAN.")
    return jsonify({"status": "success", "message": "Bot Trading Crypto berhasil dijalankan."})

@app.route("/api/stop", methods=["POST"])
def api_stop():
    bot.bot_running = False
    bot.logger.info("Bot Trading Crypto (Port 5007) DIHENTIKAN.")
    return jsonify({"status": "success", "message": "Bot Trading Crypto berhasil dihentikan."})

@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "POST":
        new_data = request.json
        cfg = bot.load_config()
        cfg.update(new_data)
        try:
            with open(bot.CONFIG_FILE, "w") as f:
                json.dump(cfg, f, indent=2)
            bot.logger.info("Konfigurasi Bot Trading Crypto diperbarui.")
            return jsonify({"status": "success", "message": "Konfigurasi disimpan."})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        return jsonify(bot.load_config())

@app.route("/api/ai-analysis", methods=["POST"])
def api_ai_analysis():
    data = request.json or {}
    symbol = data.get("symbol", "BTCUSDT")
    timeframe = data.get("timeframe", "5m")
    cfg = bot.load_config()
    res = bot.run_ai_crypto_analysis(symbol, timeframe, cfg)
    if res.get("status") == "success":
        bot.save_latest_ai_results(res, symbol=symbol)
    return jsonify(res)

@app.route("/api/indodax/test", methods=["POST"])
def api_indodax_test():
    data = request.json or {}
    cfg = bot.load_config()
    api_key = data.get("api_key") or cfg.get("indodax_api_key")
    secret_key = data.get("secret_key") or cfg.get("indodax_secret_key")
    res = exchange_api.get_indodax_account_info(api_key, secret_key)
    return jsonify(res)

@app.route("/api/gainzalgo-v2", methods=["GET"])
def api_gainzalgo_v2():
    symbol = request.args.get("symbol", "BTCUSDT")
    timeframe = request.args.get("timeframe", "5m")
    res = bot.run_gainzalgo_v2_scan(symbol, timeframe)
    return jsonify(res)

@app.route("/api/klines", methods=["GET"])
def api_klines():
    symbol = request.args.get("symbol", "BTCUSDT")
    timeframe = request.args.get("timeframe", "5m")
    limit = int(request.args.get("limit", 60))
    df = exchange_api.get_crypto_klines(symbol, timeframe, limit)
    if df is not None and not df.empty:
        return jsonify({"status": "success", "data": df.to_dict(orient="records")})
    return jsonify({"status": "error", "data": []})

@app.route("/api/positions/close", methods=["POST"])
def api_close_position():
    data = request.json or {}
    ticket = data.get("ticket")
    if ticket:
        success = exchange_api.close_paper_position(ticket)
        if success:
            return jsonify({"status": "success", "message": f"Posisi #{ticket} berhasil ditutup."})
    return jsonify({"status": "error", "message": "Gagal menutup posisi atau tiket tidak ditemukan."}), 400

@app.route("/api/positions/close-all", methods=["POST"])
def api_close_all_positions():
    count = exchange_api.close_all_paper_positions()
    return jsonify({"status": "success", "message": f"Berhasil menutup semua ({count}) posisi paper trading."})

if __name__ == "__main__":
    ensure_bot_thread()
    print("============================================================")
    print("[READY] PLATFORM BOT TRADING CRYPTO PORT 5007 IS LIVE")
    print("[URL] Access Dashboard: http://localhost:5007")
    print("============================================================")
    app.run(host="0.0.0.0", port=5007, debug=False)
