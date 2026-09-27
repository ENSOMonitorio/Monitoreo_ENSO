@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
title Monitor ENSO - Subsuperficie y Boyas TAO
echo ========================================================
echo        Monitor ENSO - Subsuperficie y Boyas TAO
echo ========================================================
echo.
echo Abriendo en el navegador: http://localhost:8050
echo.
echo Presiona Ctrl+C en esta ventana para detener el servidor.
echo ========================================================
echo.
cd /d "%~dp0backend\app\subsuperficie"
timeout /t 2 /nobreak >nul
start http://localhost:8050
"..\..\..\.venv\Scripts\python.exe" app.py
pause
