# Script de inicio rapido para Monitor ENSO en Localhost
$ErrorActionPreference = "Continue"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "       Iniciando Monitor ENSO en Localhost" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$rootPath = $PSScriptRoot
Set-Location $rootPath

# 1. Activar entorno virtual
$venvActivate = Join-Path $rootPath ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    Write-Host "[*] Activando entorno virtual (.venv)..." -ForegroundColor Green
    & $venvActivate
}

# 2. Verificar/Compilar frontend Angular si no existe backend/app/static/index.html
$staticIndex = Join-Path $rootPath "backend\app\static\index.html"
if (-not (Test-Path $staticIndex)) {
    $hasNpm = Get-Command npm -ErrorAction SilentlyContinue
    if ($hasNpm) {
        Write-Host "[*] Compilando frontend Angular por primera vez..." -ForegroundColor Yellow
        Set-Location (Join-Path $rootPath "frontend")
        npm install
        npm run build
        Set-Location $rootPath
        
        $distFolder = Join-Path $rootPath "frontend\dist\frontend\browser"
        $staticFolder = Join-Path $rootPath "backend\app\static"
        if (Test-Path $distFolder) {
            Write-Host "[*] Copiando archivos compilados a backend/app/static..." -ForegroundColor Green
            if (-not (Test-Path $staticFolder)) { New-Item -ItemType Directory -Path $staticFolder -Force | Out-Null }
            Copy-Item -Path "$distFolder\*" -Destination $staticFolder -Recurse -Force
        }
    } else {
        Write-Host "[!] Advertencia: No se encontro npm ni backend/app/static/index.html." -ForegroundColor Yellow
        Write-Host "    Instala Node.js para poder compilar el frontend Angular." -ForegroundColor Yellow
    }
}

# 3. Abrir el navegador automaticamente
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:8082"
} | Out-Null

# 4. Iniciar el servidor backend Flask
Write-Host "[*] Servidor iniciado en http://localhost:8082" -ForegroundColor Green
Write-Host "[*] Presiona Ctrl + C para detener el servidor." -ForegroundColor Gray
Write-Host ""

Set-Location (Join-Path $rootPath "backend\app")
python app.py

