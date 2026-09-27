@echo off
title Monitor ENSO - Actualizar Datos NOAA
echo ========================================================
echo        Actualizando datos de NOAA y figuras
echo ========================================================
echo.
cd /d "%~dp0"
".venv\Scripts\python.exe" backend\pipeline\fetch_and_render.py
echo.
echo ========================================================
echo        Actualizacion finalizada con exito
echo ========================================================
pause

