@echo off
title Monitor ENSO Dashboard

echo ========================================================
echo        Iniciando Monitor ENSO en Localhost
echo ========================================================
echo.

cd /d "%~dp0"

REM Agregar Node.js y npm al PATH por si se acaba de instalar
if exist "C:\Program Files\nodejs" set "PATH=C:\Program Files\nodejs;%APPDATA%\npm;%PATH%"
if exist "C:\Program Files (x86)\nodejs" set "PATH=C:\Program Files (x86)\nodejs;%PATH%"

REM Detectar Python (.venv o global)
set "PYTHON_EXE=python"
if exist "%~dp0.venv\Scripts\python.exe" set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

REM Si el frontend ya esta compilado, ir directo a iniciar el servidor
if exist "backend\app\static\index.html" goto start_server

echo [*] Frontend no compilado. Verificando Node.js / npm...
where npm >nul 2>nul
if errorlevel 1 goto no_npm

echo [*] Instalando dependencias de frontend (npm install)...
cd /d "%~dp0frontend"
call npm install
if errorlevel 1 (
    echo [!] Hubo un error al instalar paquetes npm.
    pause
    exit /b 1
)

echo [*] Compilando frontend Angular (npm run build)...
call npm run build
if errorlevel 1 (
    echo [!] Hubo un error al compilar Angular.
    pause
    exit /b 1
)
cd /d "%~dp0"

if not exist "backend\app\static" mkdir "backend\app\static"
if exist "frontend\dist\frontend\browser" xcopy /s /e /y /i "frontend\dist\frontend\browser\*" "backend\app\static\"

goto start_server

:no_npm
echo.
echo [!] ERROR: No se encontro Node.js / npm en el sistema.
echo [!] Si acabas de instalar Node.js, por favor reinicia tu computadora para refrescar variables de Windows.
echo.
pause
exit /b 1

:start_server
echo.
echo [*] Abriendo navegador web en http://localhost:8082 ...
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8082"

echo [*] Servidor iniciado en http://localhost:8082
echo [*] Para detener el servidor, cierra esta ventana o presiona Ctrl + C.
echo.

cd /d "%~dp0backend\app"
"%PYTHON_EXE%" app.py

pause
