# Rediseño · Entrega 1 (base visual y login) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el monitor actual luzca con el sistema visual nuevo (tokens, cabecera, tarjetas, gráficos Plotly claros) y que el login tenga su diseño nuevo, sin cambiar todavía las pantallas ni las rutas.

**Architecture:** Cambios de estilo en el Angular existente (`styles.scss`, cabecera en `app.html`), tema claro en `theme.py` para Plotly, y el login de Flask pasa de un string en `app.py` a una plantilla Jinja (`backend/app/templates/login.html`). Las rutas nuevas (`situacion`, `explorar/:variable`) no entran aquí: llegan con las entregas 2 y 3, cuando existan sus pantallas. Así cada entrega se publica funcionando.

**Tech Stack:** Angular 22 (vitest con `@angular/build:unit-test`), Flask + Jinja, Plotly (Python), pytest.

**Spec:** `docs/superpowers/specs/2026-11-08-rediseno-frontend-design.md` (§3, §5, §6.1, §7.3 y la cabecera de §6). Mockup: https://claude.ai/artifact/Dpe6dyJZwTmWNf73tH7M4e (pantallas «Inicio de sesión» y «Portada», para la cabecera).

## Global Constraints

- Tokens (spec §5): `--bg #F3F5F6` · `--surface #FFFFFF` · `--line #DCE2E6` · `--ink #0E2233` · `--ink-2 #45576A` · `--muted #5C6E80` · `--accent #0F5E86` · `--accent-soft #E3EEF4` · `--warm #8E1F12` / `--warm-soft #FBE8E1`.
- Colores de región = `NINO_COLORS` de `backend/app/plotting/common.py`: 1+2 `#c62828` · 3 `#2e7d32` · 3.4 `#1565c0` · 4 `#7b1fa2`.
- Fuentes: Space Grotesk (títulos, números grandes) · Inter (texto) · IBM Plex Mono (fechas, coordenadas, deltas), por Google Fonts.
- Radios 8, 12 y 16 px, iguales en las cuatro esquinas. Sin degradados ni sombras grandes. Sin emojis en la interfaz.
- El texto va en tinta (`--ink`, `--ink-2`, `--muted`), nunca del color de una serie. Los estados llevan ícono y texto.
- Se mantiene usable a ancho de celular, sin scroll horizontal de página.
- El login no muestra datos del ENSO y conserva el globo `/login-assets/past-el-nino-gif-1.webp`.
- Rama + PR. Nunca push directo a `main`. Nada de credenciales en el repo.

## Review Focus

1. **`next` del login usado para redirigir a otro sitio** (`/login?next=https://otro.sitio`): tras entrar, debe ir a `/`. Hoy `app.py` redirige a cualquier valor. Test en la Tarea 4.
2. **Mensaje de error largo del pipeline en la cabecera** («⚠ Falló la última actualización (…) — …»): no debe romper la cabecera. Se corta con «…» y el texto completo queda en `title`. Test en la Tarea 2.
3. **Pipeline corriendo:** el botón queda deshabilitado y dice «Actualizando…», para no lanzar dos corridas. Test en la Tarea 2.
4. **Login desactivado** (sin `ENSO_AUTH_PASS_HASH`, como en local y en los tests): no aparece «Salir». Test en la Tarea 2.
5. **Gráficos Plotly sobre tarjetas blancas:** ningún color oscuro heredado (texto `#e2f0e8`, marcos `#0d2a1e`, fondos `rgba(6,12,8,…)`) puede quedar ilegible. Test en la Tarea 3.

**Fuera de esta entrega** (no es un error si sigue así): la app Dash de boyas (iframe) mantiene su estilo verde hasta la entrega 4.

---

### Task 1: Tokens y base global

**Files:**
- Modify: `frontend/src/styles.scss` (bloque `:root`, `body`, scrollbar, `@import` de fuentes: líneas 1-74 actuales; y las secciones de componentes según la tabla)
- Modify: `frontend/src/index.html` (`lang="es"`, `<title>Monitor ENSO</title>`)
- Modify: `frontend/src/app/map-tab/map-tab.component.html` (solo textos: quitar «🌊 » de los dos textos de la app de boyas)

**Interfaces:**
- Produces: variables CSS `--bg --surface --line --ink --ink-2 --muted --accent --accent-soft --warm --warm-soft --r-sm(8px) --r(12px) --r-lg(16px)` y familias `--font-display: 'Space Grotesk'`, `--font-body: 'Inter'`, `--font-mono: 'IBM Plex Mono'`. Las Tareas 2 y 4 las usan.

Las clases existentes se mantienen (los componentes no cambian de marcado). Solo cambia su estilo:

| Selector | Estilo objetivo |
|---|---|
| `body` | fondo `--bg` plano (sin `radial-gradient`), texto `--ink`, `--font-body` |
| `.chart-card` (y `.map-panel`) | fondo `--surface`, borde 1px `--line`, radio `--r-lg`, padding 24px, sin `::before` ni sombra |
| `.panel-title`, `.chart-title` | `--font-display`, `--ink`; `.chart-sub` en `--muted` |
| `.chart-figure img` | fondo blanco, radio 8px, sin borde oscuro |
| `.view-toggle--vertical` + `.view-toggle-btn` | como el menú lateral del mockup: sin borde, fondo transparente, `--ink-2`, peso 500, alto mínimo 40px, radio 8px; `--active` = fondo `--accent-soft`, `--ink`, peso 600 |
| `.view-toggle-btn--sm` | segmentado: contenedor `#E6EBEE`; activo = fondo `--ink`, texto blanco |
| `.nav-section-label` | `--font-mono` 11px, mayúsculas, `--muted` |
| `.player-btn` / `--main` | 44×44 con borde `#C9D2D9` / 48px circular, fondo `--ink` |
| `.date-player-label` | `--font-mono`; `.date-player-slider` con `accent-color: var(--ink)` |
| `.enso-dropdown`, `.player-speed` | fondo blanco, borde `#C9D2D9`, radio 8px, texto `--ink` |
| `.alert-warning` | fondo `--warm-soft`, borde `#F1C9B8`, texto `--ink-2` |
| `.event-card` | fondo `--surface`, borde `--line`; `.event-year` en `--font-display` |
| `.dash-frame-container` | borde `--line`, radio `--r-lg` |
| scrollbar | pulgar `#C9D2D9`, pista transparente |

- [ ] **Step 1: Reescribir `:root`, `body` y la carga de fuentes**, con los valores de Global Constraints. Borrar las variables verdes sin uso (`--panel`, `--glass*`, `--accent-2*`, `--green`, `--border-2`, `--shadow*`).
- [ ] **Step 2: Ajustar cada selector de la tabla.** Una variable que ya no exista no puede quedar referenciada.
- [ ] **Step 3: Verificar que no queden restos de la paleta vieja**

Run: `grep -nE "#5fcf8d|#2f6b46|#1e4a30|#4a7059|#e2f0e8|#a0bfaa|var\(--panel\)|var\(--accent-2\)|var\(--glass" frontend/src/styles.scss frontend/src/app -r`
Expected: sin resultados.

- [ ] **Step 4: Compilar**

Run: `cd frontend && npm ci && npm run build`
Expected: termina sin errores.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/styles.scss frontend/src/index.html frontend/src/app/map-tab/map-tab.component.html
git commit -m "feat(frontend): sistema visual nuevo (tokens, tarjetas, controles)"
```

---

### Task 2: Cabecera y pie nuevos

**Files:**
- Modify: `frontend/src/app/app.html`
- Modify: `frontend/src/app/app.ts` (quitar `clock`, `tickClock`, `clockTimer`; agregar `statusOk`)
- Modify: `frontend/src/styles.scss` (sección HEADER y FOOTER: reemplazar `.enso-header`, `.logo*`, `.live-*`, `.header-time`, `.apply-btn`, `.logout-link`, `.enso-footer`)
- Test: `frontend/src/app/app.spec.ts`

**Interfaces:**
- Consumes: tokens de la Tarea 1; `ApiService.getConfig()`, `getStatus()`, `runPipeline()`, `getPipelineStatus()` (sin cambios).
- Produces: clases `header.app-header`, `.brand`, `.brand-name`, `.brand-sub`, `.header-status`, `.header-status--warn`, `button.header-refresh`, `a.header-logout`, `footer.app-footer`. La cabecera deja un hueco `nav.header-nav` vacío, que la entrega 2 llena con Situación / Explorar / Histórico.
- `App.statusOk: Signal<boolean>` = `!statusText().startsWith('⚠')`.

Marcado (copiado del mockup): logo SVG de 36px (círculo `--ink`, sol `#E8875E`, dos ondas) + «Monitor ENSO» (`.brand-name`, Space Grotesk 600 18px) + «Perú · Pacífico tropical» (`.brand-sub`, 12px `--muted`). A la derecha: ícono de check (o de alerta si `!statusOk`) + texto de estado en `--font-mono`, botón «Actualizar datos» con borde y «Salir». Pie: «Fuentes: NOAA OISST v2 · NCEP GDAS · NCEP GODAS · NOAA CPC · GOES-19. Pipeline propio, se actualiza cada día.» y «Monitor ENSO · referencial, no reemplaza al ENFEN».

- [ ] **Step 1: Escribir los tests que fallan** en `app.spec.ts`, reemplazando el test `should render the header`. Usar `provideHttpClientTesting()` y `HttpTestingController`, con un helper `render(config, status)` que hace `fixture.detectChanges()`, `flush` de `/api/config` y `/api/status`, otro `detectChanges()` y devuelve el elemento.

```ts
it('muestra la marca', () => {
  const el = render({ map_tabs: [], auth_enabled: false }, { text: 'Actualizado 06 nov · 07:31', is_running: false });
  expect(el.querySelector('.brand-name')?.textContent?.trim()).toBe('Monitor ENSO');
  expect(el.querySelector('.brand-sub')?.textContent?.trim()).toBe('Perú · Pacífico tropical');
  expect(el.querySelector('.live-badge')).toBeNull();
  expect(el.querySelector('.header-time')).toBeNull();
});
it('muestra el estado con el texto completo en title', () => {
  const el = render({ map_tabs: [], auth_enabled: false }, { text: 'Actualizado 06 nov · 07:31', is_running: false });
  const st = el.querySelector('.header-status')!;
  expect(st.textContent).toContain('Actualizado 06 nov · 07:31');
  expect(st.getAttribute('title')).toBe('Actualizado 06 nov · 07:31');
  expect(st.classList.contains('header-status--warn')).toBe(false);
});
it('marca advertencia cuando falló la última actualización', () => {
  const txt = '⚠ Falló la última actualización (sst_mean.nc corrupto) — Actualizado 05 nov · 07:30';
  const el = render({ map_tabs: [], auth_enabled: false }, { text: txt, is_running: false });
  expect(el.querySelector('.header-status')!.classList.contains('header-status--warn')).toBe(true);
});
it('deshabilita el botón mientras corre el pipeline', () => {
  const el = render({ map_tabs: [], auth_enabled: false }, { text: 'x', is_running: true });
  const btn = el.querySelector('button.header-refresh') as HTMLButtonElement;
  expect(btn.disabled).toBe(true);
  expect(btn.textContent?.trim()).toBe('Actualizando…');
});
it('oculta Salir sin login', () => {
  const el = render({ map_tabs: [], auth_enabled: false }, { text: 'x', is_running: false });
  expect(el.querySelector('a.header-logout')).toBeNull();
});
it('muestra Salir con login activo', () => {
  const el = render({ map_tabs: [], auth_enabled: true }, { text: 'x', is_running: false });
  expect(el.querySelector('a.header-logout')?.getAttribute('href')).toBe('/logout');
});
```

En los tests con `is_running: true`, llamar a `fixture.destroy()` al final para limpiar el `setInterval` del sondeo.

- [ ] **Step 2: Correr y ver que fallan**

Run: `cd frontend && npx ng test --watch=false`
Expected: FAIL (no existen `.brand-name`, `.header-status` ni `.header-refresh`).

- [ ] **Step 3: Implementar la cabecera y el pie** en `app.html`, `app.ts` y la sección HEADER/FOOTER de `styles.scss`. `.header-status` lleva `white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 42ch`. La cabecera usa `flex-wrap: wrap` para apilarse a ancho de celular.
- [ ] **Step 4: Correr los tests**

Run: `cd frontend && npx ng test --watch=false && npm run build`
Expected: PASS y build sin errores.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/app.html frontend/src/app/app.ts frontend/src/app/app.spec.ts frontend/src/styles.scss
git commit -m "feat(frontend): cabecera y pie con el diseño nuevo"
```

---

### Task 3: Tema claro de Plotly y colores de región unificados

**Files:**
- Modify: `backend/app/theme.py`
- Modify: `backend/app/app.py` (`INDEX_REGIONS`, líneas 84-89; `_index_region_figure`, líneas 254-306)
- Modify: `backend/app/layout_historico.py` (línea 96: `add_hline` y la llamada de la línea 97)
- Test: `backend/tests/test_theme.py` (nuevo)

**Interfaces:**
- Produces: `theme.chart_layout(**overrides) -> dict` y las constantes `theme.TEXT = "#0E2233"`, `theme.MUTED = "#5C6E80"`, `theme.GRID = "#E6EAED"`, `theme.AXIS = "#9AA7B3"`, `theme.SURFACE = "#FFFFFF"`. `dark_layout` se elimina y sus dos usos pasan a `chart_layout`.

- [ ] **Step 1: Escribir los tests que fallan** en `backend/tests/test_theme.py`. Usar `app_module = importlib.import_module("app")` y `client = app_module.server.test_client()`, como en `test_health.py`. El CSV de prueba puede seguir el patrón que ya usa `test_api_indices_region_returns_plotly_figure_json`.

```python
def test_chart_layout_is_light():
    lay = theme.chart_layout()
    assert lay["font"]["color"] == "#0E2233"
    assert lay["xaxis"]["gridcolor"] == "#E6EAED"
    assert lay["hoverlabel"]["bgcolor"] == "#0E2233"
    assert not hasattr(theme, "dark_layout")

def test_index_regions_use_the_map_box_colors():
    from plotting.common import NINO_COLORS
    for meta in app_module.INDEX_REGIONS.values():
        assert meta["color"] == NINO_COLORS[meta["label"]]

def test_index_figure_has_no_dark_leftovers(tmp_path, monkeypatch):
    # CSV mínimo de 40 días en un PROCESSED_DIR temporal (monkeypatch de app_module.PROCESSED_DIR)
    resp = client.get("/api/indices/nino12")
    body = resp.get_data(as_text=True)
    for dark in ("#0d2a1e", "rgba(6,12,8", "#e2f0e8", "#a0bfaa", "rgba(160,191,170"):
        assert dark not in body

def test_historico_figure_has_no_white_zero_line():
    body = client.get("/api/historico/oni").get_data(as_text=True)
    assert "rgba(255,255,255" not in body
```

- [ ] **Step 2: Correr y ver que fallan**

Run: `docker run --rm --user root -v "$PWD:/repo" -w /repo enso-dashboard:latest sh -c "pip install -q pytest && python -m pytest backend/tests/test_theme.py -v"`
Expected: FAIL (`chart_layout` no existe).

- [ ] **Step 3: Implementar.** `theme.py`: constantes claras y `chart_layout` con `paper_bgcolor`/`plot_bgcolor` transparentes, fuente Inter `--ink`, títulos en Space Grotesk, ejes `MUTED` sobre `GRID` y hover fondo `#0E2233` con texto blanco. `INDEX_REGIONS`: colores de `NINO_COLORS`. `_index_region_figure`: la línea cero en `theme.AXIS`, el borde de marcadores en `theme.SURFACE`, las anotaciones con fondo `theme.SURFACE` y texto `theme.TEXT`, y la nota en `theme.MUTED`. Las líneas de umbral ±0.5 usan los colores de 1+2 y 3.4 con alfa 0.75. `layout_historico.py`: `add_hline` en `theme.AXIS`.
- [ ] **Step 4: Correr toda la suite**

Run: `docker run --rm --user root -v "$PWD:/repo" -w /repo enso-dashboard:latest sh -c "pip install -q pytest && python -m pytest backend/tests -v"`
Expected: todo PASS (incluidos `test_api.py` y `test_imports.py`).

- [ ] **Step 5: Commit**

```bash
git add backend/app/theme.py backend/app/app.py backend/app/layout_historico.py backend/tests/test_theme.py
git commit -m "feat(backend): tema claro de Plotly y colores de región unificados"
```

---

### Task 4: Login rediseñado (plantilla Jinja) y `next` seguro

**Files:**
- Create: `backend/app/templates/login.html`
- Modify: `backend/app/app.py` (quitar `LOGIN_HTML`, líneas 108-180; `login()`, líneas 192-203)
- Test: `backend/tests/test_login.py` (nuevo)

**Interfaces:**
- Produces: `_safe_next(target: str | None) -> str` en `app.py`. Devuelve `target` solo si empieza con `/`, no con `//` y no contiene `\`; si no, devuelve `"/"`. `login()` renderiza `render_template("login.html", error=bool)`. La entrega 5 agregará a la plantilla la variable `google_enabled`.

Plantilla (fiel al mockup «Inicio de sesión», sin el botón de Google): dos columnas con `flex-wrap`.
- Izquierda, en blanco: logo y «Monitor ENSO» / «Perú · Pacífico tropical»; eyebrow «Monitoreo diario»; `h1` «El Niño–Oscilación del Sur»; párrafo «El estado del Pacífico tropical y del mar frente al Perú, actualizado cada día.»; tres líneas («La situación del día, explicada en simple» · «Índices Niño, mapas y su evolución en el año» · «Océano, atmósfera, boyas TAO y satélite»); el globo `/login-assets/past-el-nino-gif-1.webp` (máx. 400px) con el pie «Anomalía de TSM durante un El Niño pasado»; abajo, «Fuentes: NOAA OISST · NCEP GDAS y GODAS · TAO/TRITON · GOES-19».
- Derecha, en `--bg`: tarjeta `form method="POST"` con `h2` «Iniciar sesión», «Ingresa con el usuario del monitor.», campos Usuario (`name="username"`, `autocomplete="username"`, `autofocus`) y Contraseña (`name="password"`, `autocomplete="current-password"`) con un botón «Mostrar»/«Ocultar» (script en línea de pocas líneas que cambia `type`), el error si corresponde (`role="alert"`, «Usuario o contraseña incorrectos.»), el botón submit «Iniciar sesión» y la nota «La sesión queda abierta 7 días en este equipo.» Debajo de la tarjeta: «Uso interno. La información es referencial y no reemplaza los comunicados del ENFEN.»
- CSS en línea en la plantilla, con los tokens de Global Constraints. `<html lang="es">` y meta viewport.

- [ ] **Step 1: Escribir los tests que fallan** en `backend/tests/test_login.py`. Fixture `auth_client(monkeypatch)` con `AUTH_USER="demo"` y `AUTH_PASS_HASH=generate_password_hash("clave")` mediante monkeypatch sobre el módulo `app`.

```python
def test_login_page_renders_new_design(auth_client):
    html = auth_client.get("/login").get_data(as_text=True)
    assert "El Niño–Oscilación del Sur" in html
    assert "/login-assets/past-el-nino-gif-1.webp" in html
    assert "Iniciar sesión" in html and "Mostrar" in html
    assert "La sesión queda abierta 7 días" in html
    assert "Continuar con Google" not in html

def test_login_page_shows_no_enso_data(auth_client):
    html = auth_client.get("/login").get_data(as_text=True)
    assert "/api/" not in html and "/figures/" not in html

def test_wrong_password_shows_error(auth_client):
    html = auth_client.post("/login", data={"username": "demo", "password": "mal"}).get_data(as_text=True)
    assert "Usuario o contraseña incorrectos." in html

def test_good_login_redirects_to_next_path(auth_client):
    r = auth_client.post("/login?next=/subsurf", data={"username": "demo", "password": "clave"})
    assert r.status_code == 302 and r.headers["Location"].endswith("/subsurf")

@pytest.mark.parametrize("bad", ["https://evil.example", "//evil.example", "/\\evil.example"])
def test_good_login_ignores_external_next(auth_client, bad):
    r = auth_client.post(f"/login?next={bad}", data={"username": "demo", "password": "clave"})
    assert r.status_code == 302
    assert urlparse(r.headers["Location"]).netloc in ("", "localhost")
    assert urlparse(r.headers["Location"]).path == "/"
```

- [ ] **Step 2: Correr y ver que fallan**

Run: `docker run --rm --user root -v "$PWD:/repo" -w /repo enso-dashboard:latest sh -c "pip install -q pytest && python -m pytest backend/tests/test_login.py -v"`
Expected: FAIL (textos nuevos ausentes; `next` externo redirige afuera).

- [ ] **Step 3: Implementar** la plantilla, `_safe_next` y el `login()` con `render_template`. Borrar `LOGIN_HTML`.
- [ ] **Step 4: Correr toda la suite**

Run: el mismo comando con `backend/tests -v`.
Expected: todo PASS, incluido `test_health_bypasses_login_when_auth_enabled`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/templates/login.html backend/app/app.py backend/tests/test_login.py
git commit -m "feat(login): diseño nuevo en plantilla Jinja y redirección next segura"
```

---

### Task 5: Integración y publicación

**Files:**
- Modify: `docs/superpowers/specs/2026-11-08-rediseno-frontend-design.md` (línea 3: «Estado: aprobado (2026-11-17)»; §8: la entrega 1 queda «sistema visual + cabecera + login rediseñado + tema Plotly», las rutas nuevas pasan a las entregas 2 y 3, y el tema de Plotly sale de la entrega 4)
- Add: `HISTORIAL.md` (creado por Rocki, sin commitear)

- [ ] **Step 1: Ajustar el spec** con los dos cambios de arriba.
- [ ] **Step 2: Prueba completa en local.** `docker build -f docker/Dockerfile -t enso-dashboard:entrega1 .`; levantarlo con `docker run --rm -d -p 8099:8082 -v "$PWD/data:/app/data" --name enso-e1 enso-dashboard:entrega1`; luego `curl -s localhost:8099/ | grep -c "app-root"` (espera ≥1), `curl -s localhost:8099/api/indices/nino12 | grep -c "#c62828"` (espera ≥1) y `curl -s localhost:8099/login | grep -c "Oscilación del Sur"` (espera 1). Al final, `docker stop enso-e1`.
- [ ] **Step 3: Revisión de Cami** sobre el diff completo de la rama (antes de publicar, según CLAUDE.md). Corregir los errores reales que encuentre.
- [ ] **Step 4: Commit, push y PR.** Commit de `HISTORIAL.md` y el spec. `git push`. Dar al usuario la URL `https://github.com/ENSOMonitorio/Monitoreo_ENSO/compare/main...<rama>?expand=1` (no hay `gh` en el VPS). Esperar el check «Tests (build imagen + pytest)» en verde; el usuario hace el merge.
- [ ] **Step 5: Después del deploy.** Dodo revisa el contenedor, los logs y `/health`. Rocki agrega la entrada en `HISTORIAL.md` (qué, por qué, archivos, verificación con tests y revisiones de Cami y Dodo, y respaldo: el commit anterior a `main`, que se revierte con un PR de revert). El usuario revisa a ojo la cabecera, las tarjetas, los gráficos y el login en producción.
