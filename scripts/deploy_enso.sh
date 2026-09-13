#!/usr/bin/env bash
# Ejecutado exclusivamente por la llave SSH restringida de GitHub Actions
# (ver .github/workflows/ci-deploy.yml). No acepta argumentos del cliente:
# el forced command en authorized_keys ignora lo que el cliente pida correr.
set -euo pipefail

cd /root/ENSO_DASHBOARD

echo "==> git pull origin main"
git fetch origin main
# checkout explícito antes del reset: este VPS también se usa para trabajo
# interactivo en ramas feature (docker builds de prueba, etc.), y sin esto
# "reset --hard origin/main" reescribe silenciosamente la rama que esté
# activa en ese momento en vez de main — pudo haber tirado commits locales
# sin pushear si hubiera coincidido con trabajo en curso.
git checkout main
git reset --hard origin/main

echo "==> docker compose build"
docker compose build

echo "==> docker compose up -d --force-recreate"
docker compose up -d --force-recreate

echo "==> health check"
for i in $(seq 1 15); do
    if curl -sf http://localhost:8082/health > /dev/null; then
        echo "OK: enso_dashboard respondiendo"
        exit 0
    fi
    sleep 2
done

echo "ERROR: enso_dashboard no respondió a /health tras el deploy" >&2
exit 1
