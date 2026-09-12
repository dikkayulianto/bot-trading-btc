# PANDUAN INSTALASI & PENGGUNAAN BOT TRADING CRYPTO (PORT 5007)

## 📌 Deskripsi Platform
Platform Bot Trading Crypto Port 5007 dirancang khusus untuk perdagangan mata uang kripto (Bitcoin, Ethereum, Solana, BNB, XRP, dan koin IDR/USDT lainnya) menggunakan REST API (KuCoin, Indodax, Bybit). Platform ini beroperasi secara independen tanpa memerlukan MetaTrader 5 (MT5).

---

## ⚡ Fitur Utama
1. **Multi-Exchange REST API Direct Client**:
   - Mendukung KuCoin, Indodax, dan Bybit via REST API.
   - Tidak memerlukan MetaTrader 5 (MT5) atau DLL file.
2. **GainzAlgo V2 Alpha Signal HUD**:
   - Indikator Supertrend, EMA Crossover (9/21), RSI (14), ATR (14).
   - Penentuan target otomatis **Take Profit (TP)**, **Stop Loss (SL)** dengan Risk/Reward Ratio 1:2.0.
3. **Paper Trading Engine (Simulasi Risk-Free)**:
   - Saldo virtual $10,000.00 USDT dan Rp 150,000,000 IDR.
   - Pengujian strategi tanpa risiko kehilangan dana riil.
4. **Groq AI Analyst**:
   - Menggunakan model LLM `groq/compound-mini` (fallback `openai/gpt-oss-20b`).
   - Memberikan laporan analisis tren, support/resistance, dan skor keyakinan signal.
5. **Akses Mobile PWA (Samsung Note 3 / Android)**:
   - Web Dashboard responsif dengan fitur Progressive Web App (PWA). Bisa diinstall sebagai aplikasi 1-Click di smartphone.

---

## 🚀 Cara Menjalankan Bot
1. Double click file `RUN_BOT_PORT_5007.bat`.
2. Buka browser di laptop atau HP (dalam jaringan WiFi yang sama):
   - **Laptop**: `http://localhost:5007`
   - **HP / Samsung Note 3**: `http://[IP-LAPTOP]:5007`
3. Klik tombol **START BOT** pada Web Dashboard untuk memulai perdagangan otomatis.

---

## 🔒 Lisensi & Proteksi
- Masa berlaku lisensi dikontrol secara otomatis melalui `config.json` (`license_expire_date`).
- Untuk proteksi source code sebelum dijual ke publik, jalankan `BUILD_ENCRYPTED_RELEASE.bat` (menggunakan PyArmor).
