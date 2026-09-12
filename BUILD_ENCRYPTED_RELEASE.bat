@echo off
title BUILD ENCRYPTED RELEASE - CRYPTO BOT PORT 5007
color 0E

echo ================================================================
echo      MEMBUAT RELEASE PYARMOR ENCRYPTED FOR BOT CRYPTO PORT 5007
echo ================================================================

cd /d "%~dp0"

IF NOT EXIST "dist" mkdir dist

echo [1/3] Encrypting Python Files with PyArmor...
pyarmor gen -o dist/ app.py bot.py exchange_api.py strategy.py

echo [2/3] Copying Static Assets & Templates...
xcopy /E /I /Y templates dist\templates
xcopy /E /I /Y static dist\static
copy /Y config.json dist\config.json
copy /Y RUN_BOT_PORT_5007.bat dist\RUN_BOT_PORT_5007.bat
copy /Y PANDUAN_INSTALASI_PORT_5007.md dist\PANDUAN_INSTALASI_PORT_5007.md

echo ================================================================
echo SUCCESS! Encrypted distribution files ready in "dist\" folder.
echo ================================================================

pause
