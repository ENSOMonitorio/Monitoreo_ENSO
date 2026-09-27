@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
title Monitor ENSO - Local
echo ========================================================
echo            Iniciando Monitor ENSO (Local)
echo ========================================================
echo.
echo Abriendo en el navegador: http://localhost:8082
echo.
echo Presiona Ctrl+C en esta ventana para detener el servidor.
echo ========================================================
echo.
cd /d "%~dp0backend\app"
timeout /t 2 /nobreak >nul
start http://localhost:8082
"..\..\.venv\Scripts\python.exe" app.py
pause
