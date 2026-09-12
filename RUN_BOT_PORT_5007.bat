@echo off
title BOT TRADING CRYPTO PORT 5007 - KUCOIN / INDODAX / BYBIT
color 0A

echo ================================================================
echo      RUNNING BOT TRADING CRYPTO PLATFORM (PORT 5007)
echo ================================================================
echo Exchange: KuCoin, Indodax, Bybit REST APIs
echo Engine  : GainzAlgo V2 Alpha + Groq AI Market Analyst
echo Web UI  : http://localhost:5007
echo ================================================================

cd /d "%~dp0"

IF EXIST "C:\Users\DESKTOP\AppData\Local\Programs\Python\Python314\python.exe" (
    "C:\Users\DESKTOP\AppData\Local\Programs\Python\Python314\python.exe" app.py
) ELSE (
    python app.py
)

pause
