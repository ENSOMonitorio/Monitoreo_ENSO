# Monitor ENSO — Perú / Pacífico tropical

Dashboard de monitoreo ENOS (TSM, anomalía, viento, presión a nivel del mar,
subsuperficie) para Perú y el Pacífico tropical. Backend Flask + pipeline de
datos en Python (xarray/cartopy/matplotlib), frontend Angular — todo
empaquetado en una sola imagen Docker (multi-stage).

- **Producción:** https://monitoreoenso.igdanielporrasn.cloud
- **Deploy:** automático vía GitHub Actions al mergear a `main`
  (`.github/workflows/ci-deploy.yml`) — cada PR corre tests antes de poder
  mergear, y el deploy solo se dispara si esos tests pasan.

## Correrlo en tu propia PC

Solo hace falta tener Docker instalado — no hace falta node, conda ni GDAL
en tu máquina, todo vive dentro de la imagen.

```bash
git clone git@github.com:ENSOMonitorio/Monitoreo_ENSO.git
cd Monitoreo_ENSO
docker build -f docker/Dockerfile -t enso-dashboard:local .
docker run --rm -p 8082:8082 -v "$(pwd)/data:/app/data" enso-dashboard:local
```

Abre http://localhost:8082 — el login queda desactivado automáticamente en
local (no hay `ENSO_AUTH_PASS_HASH` seteada, mismo comportamiento que usan
los tests).

> No uses `docker compose up` para esto: `docker-compose.yml` está pensado
> para el VPS (necesita `secrets.env`, que no está en el repo, y una red
> Docker externa que solo existe ahí). El `docker build` + `docker run` de
> arriba es más simple para desarrollo local.

### Sin datos el dashboard sale vacío

`data/` no está en git (son varios GB de NetCDF/imágenes). Dos opciones:

**Opción A — copiar las figuras ya generadas (recomendado, rápido):**
Con acceso SSH al VPS, trae solo lo ya renderizado (~270 MB, no hace falta
el resto):
```bash
mkdir -p data/figures
scp -r <usuario>@<host-del-vps>:/root/ENSO_DASHBOARD/data/figures/* ./data/figures/
```

**Opción B — generarlas vos mismo (más lento, útil si tocas el pipeline):**
```bash
docker run --rm -v "$(pwd)/data:/app/data" -w /app enso-dashboard:local \
  python backend/pipeline/fetch_and_render.py
```
Descarga datos públicos de NOAA (OISST, GDAS) y genera las figuras del año
en curso. El panel de Subsuperficie (Onda Kelvin) además necesita, una sola
vez, `python backend/pipeline/build_subsurface_climatology.py` (climatología
GODAS 2015-2024).

## Tests

```bash
docker run --rm --user root -v "$(pwd):/repo" -w /repo enso-dashboard:local \
  sh -c "pip install -q pytest && python -m pytest backend/tests -v"
```

## Flujo de trabajo

Rama + Pull Request siempre — nunca push directo a `main`. Cada PR corre
tests automáticamente (build de la imagen + pytest); el deploy a producción
recién se dispara si esos tests pasan y el PR ya está mergeado a `main`.
