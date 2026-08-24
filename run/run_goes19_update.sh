#!/bin/bash
# ============================================================
# run_goes19_update.sh — actualización GOES-19 (cada 30 min)
# ============================================================
# Corre app/GOES19/goes.py dentro del contenedor enso_dashboard (ya tiene
# cartopy/gdal/boto3 instalados), vía `docker exec`. Aparte del pipeline
# diario (run_enso_update.sh): GOES-19 busca imágenes de las últimas 6
# horas, así que necesita correr mucho más seguido para estar "en vivo".
# ============================================================

set -euo pipefail

RUN_DIR="/root/ENSO_DASHBOARD/run"
LOCK_FILE="${RUN_DIR}/.run_goes19_update.lock"

if [ -f "${LOCK_FILE}" ] && kill -0 "$(cat "${LOCK_FILE}")" 2>/dev/null; then
    echo "AVISO: ya hay una corrida de GOES-19 en curso (PID $(cat "${LOCK_FILE}")). Saliendo."
    exit 0
fi
echo $$ > "${LOCK_FILE}"
trap 'rm -f "${LOCK_FILE}"' EXIT

echo "[$(date -u +%FT%TZ)] Iniciando actualización GOES-19..."

if ! docker ps --format '{{.Names}}' | grep -q '^enso_dashboard$'; then
    echo "ERROR: el contenedor enso_dashboard no está corriendo." >&2
    exit 1
fi

docker exec -w /app/app enso_dashboard python -m GOES19.goes

echo "[$(date -u +%FT%TZ)] Actualización GOES-19 completa."
