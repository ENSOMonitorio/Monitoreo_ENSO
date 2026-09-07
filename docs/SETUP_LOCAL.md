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
pip install -r backend/app/requirements.txt
```

En Windows esto funciona directo con `pip` (los wheels de `cartopy`/`gdal`/`pyproj` ya vienen precompilados en PyPI) — no hace falta Conda, aunque el `Dockerfile` de producción sí la usa.

## 3. (Opcional) Activar login local

Sin este paso la app arranca sin pedir usuario/contraseña (ver `backend/app/app.py`, `_require_login`).

Generar un hash de contraseña:

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('TU_PASSWORD'))"
```

Definir las variables de entorno antes de arrancar la app:

```bash
set ENSO_AUTH_USER=admin
set ENSO_AUTH_PASS_HASH=<hash generado arriba>
```

## 4. Arrancar el backend

```bash
cd backend/app
python app.py
```

Esto sirve la API (`/api/*`, `/figures/*`, `/health`) en **http://localhost:8082**. Sin el
frontend compilado (ver 4b), la raíz `/` devuelve 404 — `backend/app/static/` recién se
genera al construir Angular o al armar la imagen Docker.

## 4b. Ver el frontend Angular

Dos formas, desde `frontend/`:

- **Modo desarrollo** (recarga en caliente, recomendado mientras se edita):
  ```bash
  cd frontend
  npm install
  npm run start -- --proxy-config proxy.conf.json
  ```
  Abre **http://localhost:4200** (el backend de 8082 debe estar corriendo — el proxy le
  reenvía `/api`, `/figures`, `/login`, `/logout` y `/health`).

- **Build de producción servido por el propio Flask** (para probar tal cual queda en Docker):
  ```bash
  cd frontend
  npm install
  npm run build
  ```
  Copia el contenido de `frontend/dist/frontend/browser/` a `backend/app/static/` y abre
  **http://localhost:8082**.

## 5. Poblar con datos reales de NOAA

Desde la raíz del proyecto (no desde `backend/app/`), con el entorno activado:

```bash
python backend/pipeline/fetch_and_render.py
```

Descarga SST, viento y SLP del año actual, y genera las figuras en `data/figures/`. Puede tardar varios minutos según la conexión.

## 6. (Una sola vez) Habilitar el panel de subsuperficie / Onda Kelvin

```bash
python backend/pipeline/build_subsurface_climatology.py
```

Descarga 10 años de datos GODAS (2015-2024, configurable con argumentos) para construir la climatología base en `data/processed/godas_climatology.nc`. Después de correr esto, vuelve a ejecutar el paso 5 para que se genere ese panel.

## 7. Flujo de git para subir cambios (rama -> commit -> push)

`main` está protegida — los cambios se suben por una rama y un pull request, no directo a `main`.

Crear la rama (desde `main` actualizado):

```bash
git checkout main
git pull origin main
git checkout -b nombre-de-tu-rama
```

Hacer tus cambios en el código, luego revisar qué se modificó:

```bash
git status
git diff
```

Agregar los archivos al staging:

```bash
git add archivo1.py archivo2.py
```

Crear el commit:

```bash
git commit -m "Descripción corta de qué cambió y por qué"
```

Subir la rama a GitHub (primera vez, para vincularla con `-u`):

```bash
git push -u origin nombre-de-tu-rama
```

Las veces siguientes en esa misma rama, ya alcanza con:

```bash
git push
```

Después de esto, el pull request y el merge hacia `main` se hacen desde la web de GitHub:

1. Entra a https://github.com/ENSOMonitorio/Monitoreo_ENSO/pulls y click en **"New pull request"**
2. **base:** `main` — **compare:** tu rama
3. Completa título y descripción, click en **"Create pull request"**
4. Espera a que el workflow de CI (`ci-deploy.yml`) corra los tests y quede en verde ✅
5. Click en **"Merge pull request"** -> **"Confirm merge"**
6. Opcional: borrar la rama con el botón que aparece después del merge

## Notas

- `data/` y `secrets.env` están en `.gitignore` — nunca se comparten entre máquinas. Cada copia local descarga y genera los suyos.
- Esta copia local es completamente independiente del VPS de producción: no comparte datos, sesión ni credenciales.
- Alternativa: correr todo con Docker (`docker-compose up --build`), que replica el entorno de producción (Conda + GDAL). Para esto localmente hace falta además crear `secrets.env` y la red externa `docker_vps_network` (`docker network create docker_vps_network`), o remover esa red del `docker-compose.yml` para uso local.
