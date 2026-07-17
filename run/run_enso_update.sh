#!/bin/bash
# ============================================================
# run_enso_update.sh — actualización diaria Monitor ENSO
# ============================================================
# Descarga NOAA (OISST + NCEP/NCAR Reanalysis), regenera las figuras y el
# índice de tendencia dentro del contenedor enso_dashboard (ya tiene xarray/
# cartopy instalados), vía `docker exec`.
# ============================================================

set -euo pipefail

RUN_DIR="/root/ENSO_DASHBOARD/run"
LOCK_FILE="${RUN_DIR}/.run_enso_update.lock"

if [ -f "${LOCK_FILE}" ] && kill -0 "$(cat "${LOCK_FILE}")" 2>/dev/null; then
    echo "AVISO: ya hay una corrida en curso (PID $(cat "${LOCK_FILE}")). Saliendo."
    exit 0
fi
echo $$ > "${LOCK_FILE}"
trap 'rm -f "${LOCK_FILE}"' EXIT

echo "[$(date -u +%FT%TZ)] Iniciando actualización ENSO..."

if ! docker ps --format '{{.Names}}' | grep -q '^enso_dashboard$'; then
    echo "ERROR: el contenedor enso_dashboard no está corriendo." >&2
    exit 1
fi

docker exec -w /app enso_dashboard python pipeline/fetch_and_render.py

echo "[$(date -u +%FT%TZ)] Actualización ENSO completa."
