# Bot Trading Crypto (BTC & Altcoins) - GainzAlgo V2 Alpha & Groq AI

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Platform Bot Trading Cryptocurrency otomatis berbasis Web Dashboard (Port 5007) dengan mesin analisis kuantitatif **GainzAlgo V2 Alpha**, integrasi **Groq AI Analyst**, simulasi **Paper Trading ($10.000 USDT)**, dan konektivitas live market ke **KuCoin**, **Indodax**, dan **Bybit** via REST API.

---

## Fitur Utama

- **Multi-Exchange REST Client**: Mengambil data ticker dan candlestick (klines) real-time dari KuCoin, Indodax, dan Bybit secara langsung tanpa broker pihak ketiga.
- **GainzAlgo V2 Alpha HUD**:
  - Deteksi sinyal BUY / SELL / HOLD otomatis.
  - Kalkulasi level Entry, Take Profit (TP), dan Stop Loss (SL) presisi rasio Risk/Reward 1:2.
  - Indikator teknikal multi-layer: Supertrend, EMA 9/21, RSI 14, ATR 14.
- **Groq AI Market Intelligence**: Analisis sentimen pasar dan validasi sinyal menggunakan model AI ultra-cepat dari Groq Cloud.
- **Paper Trading Engine**: Portofolio virtual default $10.000 USDT (Rp 150.000.000) untuk pengujian strategi tanpa risiko saldo riil.
- **Interactive Cyberpunk Web Dashboard (Port 5007)**:
  - Live TradingView Chart Widget.
  - Multi-Coin Switcher (BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT).
  - Monitoring posisi real-time dengan tombol *Tutup Posisi* dan *Tutup Semua Posisi*.
  - Terminal System Logs streaming real-time.
- **In-Memory Micro-Caching**: Optimasi latensi respons ~98 ms dan proteksi rate-limit API exchange.

---

## Struktur Proyek

```
.
├── app.py                     # Server Flask utama (Port 5007) & background worker
├── bot.py                     # Siklus eksekusi trading, manajemen lisensi & AI Groq
├── strategy.py                # Algoritma GainzAlgo V2 (Supertrend, EMA, RSI, ATR)
├── exchange_api.py            # Konektor REST API KuCoin/Indodax & Paper Trading manager
├── config.example.json        # Template konfigurasi parameter bot
├── requirements.txt           # Dependensi Python
├── RUN_BOT_PORT_5007.bat      # Script launcher sekali klik (Windows)
├── static/                    # Aset frontend (CSS Cyberpunk, JS app, Icons, Manifest)
│   ├── css/style.css
│   └── js/app.js
└── templates/
    └── index.html             # Tampilan dashboard web utama
```

---

## Panduan Instalasi & Menjalankan

### 1. Clone Repository
```bash
git clone https://github.com/dikkayulianto/bot-trading-btc.git
cd bot-trading-btc
```

### 2. Buat & Aktifkan Virtual Environment (Opsional tapi Disarankan)
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 3. Install Dependensi
```bash
pip install -r requirements.txt
```

### 4. Konfigurasi
Salin `config.example.json` menjadi `config.json`:
```bash
cp config.example.json config.json
```
Edit `config.json` sesuai kebutuhan (masukkan Groq API Key Anda jika ingin mengaktifkan Groq AI Analyst):
```json
{
  "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"],
  "timeframe": "5m",
  "paper_trading": true,
  "trade_amount_usdt": 100.0,
  "sl_percent": 1.5,
  "tp_percent": 3.0,
  "groq_api_key": "gsk_YOUR_KEY_HERE"
}
```

### 5. Jalankan Bot
```bash
python app.py
```
Atau klik ganda file `RUN_BOT_PORT_5007.bat` di Windows.

Buka browser Anda dan akses:
```
http://localhost:5007
```

---

## Lisensi
Proyek ini dilisensikan di bawah [MIT License](LICENSE).
