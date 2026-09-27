@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
title Subsuperficie - Boyas TAO Dash
cd /d "%~dp0"
echo ========================================================
echo        Iniciando Dash Subsuperficie (Puerto 8050)
echo ========================================================
start http://localhost:8050
"..\..\..\.venv\Scripts\python.exe" app.py
pause
