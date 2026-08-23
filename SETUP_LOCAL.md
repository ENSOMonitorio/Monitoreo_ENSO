# Levantar el dashboard en local

Guía para correr una copia local de Monitor ENSO, independiente del VPS de producción.

## 1. Clonar el repositorio

```bash
git clone git@github.com:ENSOMonitorio/Monitoreo_ENSO.git
cd Monitoreo_ENSO
```

Requiere tener una clave SSH agregada a tu cuenta de GitHub con acceso al repo. Verifica con:

```bash
ssh -T git@github.com
```

## 2. Crear entorno virtual e instalar dependencias

```bash
python -m venv .venv
.venv\Scripts\activate          # PowerShell/CMD
pip install --upgrade pip
pip install -r app/requirements.txt
```

En Windows esto funciona directo con `pip` (los wheels de `cartopy`/`gdal`/`pyproj` ya vienen precompilados en PyPI) — no hace falta Conda, aunque el `Dockerfile` de producción sí la usa.

## 3. (Opcional) Activar login local

Sin este paso la app arranca sin pedir usuario/contraseña (ver `app/app.py`, `_require_login`).

Generar un hash de contraseña:

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('TU_PASSWORD'))"
```

Definir las variables de entorno antes de arrancar la app:

```bash
set ENSO_AUTH_USER=admin
set ENSO_AUTH_PASS_HASH=<hash generado arriba>
```

## 4. Arrancar el dashboard

```bash
cd app
python app.py
```

Abre **http://localhost:8082**

## 5. Poblar con datos reales de NOAA

Desde la raíz del proyecto (no desde `app/`), con el entorno activado:

```bash
python pipeline/fetch_and_render.py
```

Descarga SST, viento y SLP del año actual, y genera las figuras en `data/figures/`. Puede tardar varios minutos según la conexión.

## 6. (Una sola vez) Habilitar el panel de subsuperficie / Onda Kelvin

```bash
python pipeline/build_subsurface_climatology.py
```

Descarga 10 años de datos GODAS (2015-2024, configurable con argumentos) para construir la climatología base en `data/processed/godas_climatology.nc`. Después de correr esto, vuelve a ejecutar el paso 5 para que se genere ese panel.

## Notas

- `data/` y `secrets.env` están en `.gitignore` — nunca se comparten entre máquinas. Cada copia local descarga y genera los suyos.
- Esta copia local es completamente independiente del VPS de producción: no comparte datos, sesión ni credenciales.
- Alternativa: correr todo con Docker (`docker-compose up --build`), que replica el entorno de producción (Conda + GDAL). Para esto localmente hace falta además crear `secrets.env` y la red externa `docker_vps_network` (`docker network create docker_vps_network`), o remover esa red del `docker-compose.yml` para uso local.
